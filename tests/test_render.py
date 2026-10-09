import math

import pandas as pd
import shapely

from landuse_map.data import Place, RegionSample, load_region
from landuse_map.render import (
    _ramp,
    map_document,
    map_iframe,
    stats_markdown,
    summary_table,
)

REGION = "testland-latest"
NO_DATA = "#94a3b8"


def test_ramp_hits_the_ends_and_clamps():
    assert _ramp(0.0) == "#f7fcb9"
    assert _ramp(1.0) == "#00441b"
    assert _ramp(-3.0) == "#f7fcb9"
    assert _ramp(7.0) == "#00441b"


def test_ramp_breakpoints_and_blends():
    assert _ramp(1 / 3) == "#addd8e"
    assert _ramp(2 / 3) == "#31a354"
    assert _ramp(0.2) == "#cbe99f"


def test_nan_is_no_data_grey():
    assert _ramp(math.nan) == NO_DATA


def test_map_document_escapes_hostile_names():
    hostile = Place(
        osm_type="way",
        osm_id=9,
        name="<img src=x>",
        timestamp="",
        area_m2=1.0,
        tags={},
        geometry=shapely.box(0, 0, 1, 1),
        texts=(),
    )
    doc = map_document([hostile], "share_yes")
    assert "<img src=x>" not in doc
    assert "&lt;img src=x&gt;" in doc


def test_legend_names_the_colour_mode():
    share = map_document([], "share_yes")
    area = map_document([], "area_m2")
    assert "Share of yes" in share
    assert "Share of yes" not in area
    assert "Area" in area


def test_map_iframe_embeds_the_escaped_document():
    frame = map_iframe(load_region(REGION), "share_yes")
    assert frame.startswith('<iframe srcdoc="&lt;!DOCTYPE html&gt;')
    assert frame.endswith("</iframe>")


def test_summary_table_has_one_row_per_place():
    table = summary_table(load_region(REGION).places)
    assert len(table) == 3
    assert list(table.columns) == [
        "name",
        "type",
        "area_m2",
        "sentences",
        "yes",
        "no",
        "failed",
        "share_yes",
        "landuse",
        "osm",
    ]


def test_summary_table_values():
    table = summary_table(load_region(REGION).places)
    farm = table[table.osm == "https://www.openstreetmap.org/way/1"].iloc[0]
    assert (farm.yes, farm.no, farm.failed, farm.sentences) == (1, 1, 0, 3)
    assert farm.share_yes == 0.5
    assert farm.landuse == "farmland"
    ruin = table[table.osm == "https://www.openstreetmap.org/way/2"].iloc[0]
    assert ruin.failed == 1
    assert pd.isna(ruin.share_yes)


def test_stats_markdown_reports_counts():
    text = stats_markdown(load_region(REGION))
    assert "showing **3** of 3 polygons" in text
    assert "1 yes · 1 no · share yes 50%" in text


def test_stats_markdown_without_judgements_has_no_share():
    text = stats_markdown(RegionSample(region="empty", places=[], total=0))
    assert "share yes –" in text
