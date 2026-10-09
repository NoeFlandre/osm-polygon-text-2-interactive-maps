import math
from collections import Counter

import pandas as pd
import shapely
from helpers import page_data, page_places

from landuse_map.data import NO, YES, Place, RegionSample, Sentence, Text, load_region
from landuse_map.render import (
    BASEMAP_URL,
    CATEGORY_COLOR,
    CATEGORY_NAME,
    LEAFLET_CSS_SRI,
    LEAFLET_JS,
    LEAFLET_JS_SRI,
    NO_TEXT_HTML,
    _category,
    _color,
    _json_for_script,
    _legend_html,
    _pct,
    _tooltip_html,
    area_payload,
    map_document,
    stats_markdown,
    summary_table,
)

REGION = "testland-latest"
YES_COLOR = CATEGORY_COLOR["yes"]
NO_COLOR = CATEGORY_COLOR["no"]
MIXED_COLOR = CATEGORY_COLOR["mixed"]
NONE_COLOR = CATEGORY_COLOR["none"]


def place(*texts: Text, **overrides) -> Place:
    fields = {
        "osm_type": "way",
        "osm_id": 9,
        "name": "Test",
        "timestamp": "2024-01-02",
        "area_m2": 1.0,
        "tags": {},
        "geometry": shapely.box(0, 0, 1, 1),
        "texts": tuple(texts),
    }
    fields.update(overrides)
    return Place(**fields)


def only(label: str, text: str = "a sentence") -> Place:
    return place(Text("description", (Sentence(text, label),)))


def test_map_document_is_one_full_page_map():
    doc = map_document(load_region(REGION).places)
    assert doc.startswith("<!DOCTYPE html>")
    assert "<title>Land-use map</title>" in doc
    assert LEAFLET_JS in doc


def test_page_data_has_one_record_per_place():
    places = load_region(REGION).places
    records = page_places(map_document(places))
    assert len(records) == len(places)


def test_record_holds_color_counts_area_and_tooltip():
    farm = load_region(REGION).places[0]
    record = page_places(map_document([farm]))[0]
    assert record["color"] == MIXED_COLOR
    assert (record["yes"], record["no"]) == (1, 1)
    assert record["area"] == 100.0
    assert record["tip"] == _tooltip_html(farm)


def test_record_has_the_polygon_geometry_and_a_hit_point_inside_it():
    farm = load_region(REGION).places[0]
    record = page_places(map_document([farm]))[0]
    assert record["polygon"]["type"] in {"Polygon", "MultiPolygon"}
    lat, lng = record["hit"]
    assert shapely.contains_xy(farm.geometry, lng, lat)


def test_hit_markers_are_small_and_nearly_transparent():
    assert page_data(map_document([only(YES)]))["hit"] == {"radius": 6, "opacity": 0.01}


def test_area_payload_names_the_area_and_its_total():
    places = load_region(REGION).places
    payload = area_payload("Testland", places, total=5)
    assert payload["name"] == "Testland"
    assert payload["total"] == 5
    assert len(payload["places"]) == len(places)


def test_bounds_cover_all_places():
    data = page_data(map_document(load_region(REGION).places))
    assert data["area"]["bounds"] == [[0.0, 0.0], [1.0, 5.0]]


def test_bounds_are_none_without_places():
    assert page_data(map_document([]))["area"]["bounds"] is None


def test_basemap_is_the_openstreetmap_tile_server():
    assert page_data(map_document([]))["basemap"]["url"] == BASEMAP_URL


def test_page_has_the_stats_and_the_area_slider():
    doc = map_document([only(YES)])
    for element_id in [
        "stat-polygons",
        "stat-yes",
        "stat-no",
        "min-area",
        "min-area-label",
    ]:
        assert f'id="{element_id}"' in doc


def test_json_escapes_markup_so_the_page_stays_intact():
    doc = map_document([only(YES)])
    assert "\\u003cdiv\\u003e" in doc
    assert doc.count("</script>") == 3


def test_json_for_script_escapes_ampersand_angle_brackets_and_separators():
    text = _json_for_script({"a": "x & y <z>    "})
    assert "\\u0026" in text
    assert "\\u003c" in text and "\\u003e" in text
    assert "\\u2028" in text and "\\u2029" in text
    assert "<" not in text and ">" not in text


def test_tooltip_shows_the_label_and_text_of_each_sentence():
    html = _tooltip_html(load_region(REGION).places[0])
    assert "<b>label</b>: yes<br><b>text</b>: Fields of crops." in html
    assert "<b>label</b>: no<br><b>text</b>: Cows graze." in html
    assert "farmland" not in html


def test_tooltip_escapes_osm_text():
    hostile = only(YES, "<b>bold</b>")
    html = _tooltip_html(hostile)
    assert "<b>bold</b>" not in html
    assert "&lt;b&gt;bold&lt;/b&gt;" in html


def test_tooltip_labels_unknown_values_by_their_code():
    odd = only("weird", "word")
    assert "<b>label</b>: weird<br><b>text</b>: word" in _tooltip_html(odd)


def test_tooltip_skips_empty_sentences():
    gap = place(Text("description", (Sentence("", NO), Sentence("Cows graze.", NO))))
    html = _tooltip_html(gap)
    assert html.count("<b>text</b>") == 1
    assert "Cows graze." in html


def test_tooltip_says_no_description_text_when_there_is_none():
    assert _tooltip_html(place()) == NO_TEXT_HTML
    assert "no description text" in _tooltip_html(place())


def test_tooltip_uses_a_description_variant_when_the_tag_is_missing():
    english = Text("description:en", (Sentence("English text", YES),))
    assert "English text" in _tooltip_html(place(english))


def test_tooltip_prefers_description_over_its_variants():
    english = Text("description:en", (Sentence("English", NO),))
    local = Text("description", (Sentence("Local", YES),))
    html = _tooltip_html(place(english, local))
    assert "Local" in html
    assert "English" not in html


def test_category_yes_only_no_only_and_mixed_and_none():
    assert _category(only(YES)) == "yes"
    assert _category(only(NO)) == "no"
    both = place(Text("description", (Sentence("a", YES), Sentence("b", NO))))
    assert _category(both) == "mixed"
    assert _category(place()) == "none"
    assert _category(only("failed")) == "none"


def test_category_colors_are_four_distinct_colors():
    assert len({YES_COLOR, NO_COLOR, MIXED_COLOR, NONE_COLOR}) == 4
    both = place(Text("description", (Sentence("a", YES), Sentence("b", NO))))
    assert _color(only(YES)) == YES_COLOR
    assert _color(only(NO)) == NO_COLOR
    assert _color(both) == MIXED_COLOR
    assert _color(place()) == NONE_COLOR


def test_page_colors_each_polygon_by_its_category():
    records = page_places(map_document([only(YES), only(NO)]))
    assert [r["color"] for r in records] == [YES_COLOR, NO_COLOR]


def test_legend_lists_every_category_with_its_color():
    legend = _legend_html()
    assert "Polygon color" in legend
    for key, name in CATEGORY_NAME.items():
        assert name in legend
        assert legend.count(CATEGORY_COLOR[key]) == 1


def test_map_document_contains_the_legend():
    doc = map_document([only(YES)])
    assert "Polygon color" in doc
    assert "only yes" in doc and "only no" in doc


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
    assert (farm.yes, farm.no, farm.failed, farm.sentences) == (1, 1, 0, 2)
    assert farm.share_yes == 0.5
    assert farm.landuse == "farmland"
    ruin = table[table.osm == "https://www.openstreetmap.org/way/2"].iloc[0]
    assert ruin.failed == 1
    assert pd.isna(ruin.share_yes)


def test_summary_table_rounds_share_and_area():
    third = place(
        Text(
            "description",
            (Sentence("a", YES), Sentence("b", NO), Sentence("c", NO)),
        ),
        area_m2=1466.487,
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


def test_fixture_polygons_get_the_expected_categories():
    colors = Counter(_color(p) for p in load_region(REGION).places)
    assert colors == Counter({MIXED_COLOR: 1, NONE_COLOR: 2})


def test_empty_table_keeps_its_header():
    from landuse_map.render import TABLE_COLUMNS

    table = summary_table([])
    assert list(table.columns) == TABLE_COLUMNS
    assert len(table) == 0


def test_leaflet_tags_carry_integrity_hashes():
    doc = map_document([only(YES)])
    assert f'integrity="{LEAFLET_CSS_SRI}"' in doc
    assert f'integrity="{LEAFLET_JS_SRI}"' in doc
    assert 'crossorigin=""' in doc


def test_tile_layer_stops_at_the_native_zoom_of_the_basemap():
    doc = map_document([only(YES)])
    assert "maxNativeZoom: 19" in doc


def test_page_data_rejects_nan_and_infinity():
    import math

    import pytest

    from landuse_map.render import _json_for_script

    with pytest.raises(ValueError):
        _json_for_script({"area": math.nan})
    with pytest.raises(ValueError):
        _json_for_script({"area": math.inf})


def test_area_file_rejects_a_nan_area():
    import math

    import pytest

    from landuse_map.render import area_json

    nan_area = place(area_m2=math.nan)
    with pytest.raises(ValueError):
        area_json(area_payload("Testland", [nan_area], total=1))
