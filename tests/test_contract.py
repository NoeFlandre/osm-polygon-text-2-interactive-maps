"""Property tests. Every polygon must show hover text, whatever its tags say."""

import re
from html import escape

import shapely
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from landuse_map.data import FAILED, NO, SKIPPED, YES, Place, Sentence, Text
from landuse_map.render import (
    CATEGORY_COLOR,
    _category,
    _color,
    _tooltip_html,
    map_document,
)

LABELS = st.sampled_from([YES, NO, FAILED, SKIPPED, "unexpected"])
TAG_KEYS = st.sampled_from(
    [
        "description",
        "description:en",
        "description:de",
        "description:cs",
        "name",
        "landuse",
    ]
)
SENTENCES = st.builds(Sentence, text=st.text(max_size=60), label=LABELS)
TEXTS = st.builds(
    Text, tag_key=TAG_KEYS, sentences=st.lists(SENTENCES, max_size=5).map(tuple)
)
PLACES = st.builds(
    Place,
    osm_type=st.sampled_from(["way", "relation"]),
    osm_id=st.integers(min_value=1, max_value=10**12),
    name=st.text(max_size=40),
    timestamp=st.sampled_from(["", "2024-01-02"]),
    area_m2=st.floats(min_value=0.0, max_value=1e9, allow_nan=False),
    tags=st.dictionaries(
        st.sampled_from(["landuse", "natural", "name"]),
        st.text(max_size=12),
        max_size=3,
    ),
    geometry=st.just(shapely.box(0, 0, 1, 1)),
    texts=st.lists(TEXTS, max_size=4).map(tuple),
)

FAST = settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
SLOW = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
OUR_TAGS = re.compile(r'</?(div|b|br)( class="lu")?>')


def visible(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


@FAST
@given(PLACES)
def test_every_polygon_has_visible_hover_text(place):
    assert visible(_tooltip_html(place)) != ""


@FAST
@given(PLACES)
def test_hover_text_contains_only_our_markup(place):
    html = OUR_TAGS.sub("", _tooltip_html(place))
    assert "<" not in html
    assert ">" not in html


@FAST
@given(PLACES)
def test_every_visible_sentence_is_shown_escaped(place):
    html = _tooltip_html(place)
    for sentence in place.visible_sentences:
        assert escape(sentence.text) in html


@FAST
@given(PLACES)
def test_every_polygon_gets_one_known_color(place):
    assert _color(place) in set(CATEGORY_COLOR.values())


@FAST
@given(PLACES)
def test_category_follows_the_labels_shown(place):
    labels = {s.label for s in place.visible_sentences}
    category = _category(place)
    if YES in labels and NO in labels:
        assert category == "mixed"
    elif YES in labels:
        assert category == "yes"
    elif NO in labels:
        assert category == "no"
    else:
        assert category == "none"


@SLOW
@given(PLACES)
def test_map_draws_each_polygon_with_its_color_and_a_hit_marker(place):
    doc = map_document([place])
    assert doc.count("L.geoJson(") == 1
    assert doc.count("L.circleMarker(") == 1
    assert f'"fillColor": "{_color(place)}"' in doc
