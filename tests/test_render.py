import math

import pandas as pd
import shapely

from landuse_map.data import NO, YES, Place, RegionSample, Sentence, Text, load_region
from landuse_map.render import (
    FILL,
    _highlight,
    _pct,
    _style,
    _tooltip_html,
    map_document,
    stats_markdown,
    summary_table,
)

REGION = "testland-latest"


def tooltip(p: Place) -> str:
    html = _tooltip_html(p)
    assert html is not None
    return html


def place(**overrides) -> Place:
    fields = {
        "osm_type": "way",
        "osm_id": 9,
        "name": "Test",
        "timestamp": "2024-01-02",
        "area_m2": 1.0,
        "tags": {},
        "geometry": shapely.box(0, 0, 1, 1),
        "texts": (),
    }
    fields.update(overrides)
    return Place(**fields)


def test_map_document_is_one_full_page_map():
    doc = map_document(load_region(REGION).places)
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>Land-use map</title>" in doc


def test_map_document_fits_the_view_to_the_places():
    doc = map_document(load_region(REGION).places)
    assert "[[0.0, 0.0], [1.0, 5.0]]" in doc


def test_map_document_without_places_does_not_fit():
    assert "fitBounds" not in map_document([])


def test_tooltip_shows_the_label_and_text_of_each_sentence():
    farm = load_region(REGION).places[0]
    html = tooltip(farm)
    assert "<b>label</b>: yes<br><b>text</b>: Fields of crops." in html
    assert "<b>label</b>: no<br><b>text</b>: Cows graze." in html
    assert "landuse" not in html
    assert "farmland" not in html


def test_tooltip_omits_the_name_and_links():
    html = tooltip(load_region(REGION).places[0])
    assert "Farm" not in html
    assert "openstreetmap" not in html


def test_tooltip_is_absent_without_a_description():
    assert _tooltip_html(place()) is None


def test_tooltip_escapes_osm_text():
    hostile = place(texts=(Text("description", (Sentence("<b>bold</b>", YES),)),))
    html = tooltip(hostile)
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_tooltip_uses_only_the_description_tag():
    other = place(
        texts=(Text("description:en", (Sentence("English text", YES),)),),
    )
    assert _tooltip_html(other) is None


def test_tooltip_labels_unknown_values_by_their_code():
    odd = place(texts=(Text("description", (Sentence("word", "weird"),)),))
    assert "<b>label</b>: weird<br><b>text</b>: word" in tooltip(odd)


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


def test_summary_table_rounds_share_and_area():
    third = place(
        area_m2=1466.487,
        texts=(
            Text(
                "description",
                (Sentence("a", YES), Sentence("b", NO), Sentence("c", NO)),
            ),
        ),
    )
    row = summary_table([third]).iloc[0]
    assert row.share_yes == 0.333
    assert row.area_m2 == 1466


def test_summary_table_uses_blank_landuse_when_missing():
    assert summary_table([place()]).iloc[0].landuse == ""


def test_stats_markdown_reports_counts():
    text = stats_markdown(load_region(REGION))
    assert "showing **3** of 3 polygons" in text
    assert "1 yes · 1 no · share yes 50%" in text


def test_stats_markdown_without_judgements_has_no_share():
    text = stats_markdown(RegionSample(region="empty", places=[], total=0))
    assert "share yes –" in text


def test_pct_rounds_to_whole_percent_and_marks_nan():
    assert _pct(0.5899) == "59%"
    assert _pct(math.nan) == "–"


def test_map_document_draws_polygons_with_the_fill_and_tooltip():
    doc = map_document(load_region(REGION).places)
    assert f'"fillColor": "{FILL}"' in doc
    assert "<b>label</b>: yes" in doc
    assert "Control scale" not in doc
    assert "L.control.scale" in doc


def test_polygon_style_and_highlight_values():
    assert _style({}) == {
        "fillColor": FILL,
        "color": "#134e4a",
        "weight": 1,
        "fillOpacity": 0.45,
    }
    assert _highlight({}) == {"weight": 3, "fillOpacity": 0.75}


def test_tooltip_wraps_long_text_inside_the_page():
    doc = map_document(load_region(REGION).places)
    assert "white-space: normal !important;" in doc
    assert "width: max-content;" in doc
    assert "opacity: 1 !important;" in doc
    assert "max-width: 320px;" in doc


def test_tooltip_skips_empty_sentences():
    gap = place(
        texts=(
            Text(
                "description",
                (Sentence("", NO), Sentence("Cows graze.", NO)),
            ),
        ),
    )
    html = tooltip(gap)
    assert "<b>label</b>: no<br><b>text</b>: Cows graze." in html
    assert html.count("<b>text</b>") == 1


def test_tooltip_is_absent_when_every_sentence_is_empty():
    assert (
        _tooltip_html(place(texts=(Text("description", (Sentence(" ", NO),)),))) is None
    )
