import math
from collections import Counter

import pandas as pd
import shapely

from landuse_map.data import NO, YES, Place, RegionSample, Sentence, Text, load_region
from landuse_map.render import (
    CATEGORY_COLOR,
    CATEGORY_NAME,
    NO_TEXT_HTML,
    _category,
    _color,
    _legend_html,
    _pct,
    _style,
    _tooltip_html,
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


def test_map_document_fits_the_view_to_the_places():
    doc = map_document(load_region(REGION).places)
    assert "[[0.0, 0.0], [1.0, 5.0]]" in doc


def test_map_document_without_places_does_not_fit():
    assert "fitBounds" not in map_document([])


def test_map_document_draws_one_polygon_and_one_hit_marker_per_place():
    places = load_region(REGION).places
    doc = map_document(places)
    assert doc.count("L.geoJson(") == len(places)
    assert doc.count("L.circleMarker(") == len(places)


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
    assert (
        _category(place(Text("description", (Sentence("a", YES), Sentence("b", NO)))))
        == "mixed"
    )
    assert _category(place()) == "none"
    assert _category(only("failed")) == "none"


def test_category_colors_are_four_distinct_colors():
    colors = [YES_COLOR, NO_COLOR, MIXED_COLOR, NONE_COLOR]
    assert len(set(colors)) == 4
    assert _color(only(YES)) == YES_COLOR
    assert _color(only(NO)) == NO_COLOR
    assert (
        _color(place(Text("description", (Sentence("a", YES), Sentence("b", NO)))))
        == MIXED_COLOR
    )
    assert _color(place()) == NONE_COLOR


def test_map_document_uses_the_category_color_of_each_polygon():
    assert f'"fillColor": "{YES_COLOR}"' in map_document([only(YES)])
    assert f'"fillColor": "{NO_COLOR}"' in map_document([only(NO)])


def test_legend_lists_every_category_with_its_color():
    legend = _legend_html()
    assert "Polygon color" in legend
    for key, name in CATEGORY_NAME.items():
        assert name in legend
        assert CATEGORY_COLOR[key] in legend
    assert "yes and no" in legend


def test_map_document_contains_the_legend():
    doc = map_document([only(YES)])
    assert "Polygon color" in doc
    assert "only yes" in doc and "only no" in doc


def test_polygon_style_values():
    assert _style(YES_COLOR)({}) == {
        "fillColor": YES_COLOR,
        "color": YES_COLOR,
        "weight": 1,
        "fillOpacity": 0.5,
    }


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


def test_highlight_values():
    from landuse_map.render import _highlight

    assert _highlight({}) == {"weight": 3, "fillOpacity": 0.75}


def test_hit_markers_are_small_and_nearly_transparent():
    doc = map_document([only(YES)])
    assert '"radius": 6' in doc
    assert '"fillOpacity": 0.01' in doc


def test_legend_has_one_swatch_per_category_color():
    legend = _legend_html()
    for color in CATEGORY_COLOR.values():
        assert legend.count(color) == 1
