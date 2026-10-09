import math

import pandas as pd
import shapely

from landuse_map.data import (
    FAILED,
    NO,
    SKIPPED,
    YES,
    Place,
    Sentence,
    Text,
    _date,
    _text_or,
    load_region,
)

REGION = "testland-latest"


def by_id(places):
    return {p.osm_id: p for p in places}


def test_places_carry_their_texts_and_labels():
    farm = by_id(load_region(REGION).places)[1]
    assert farm.texts == (
        Text(
            "description",
            (Sentence("Fields of crops.", YES), Sentence("Cows graze.", NO)),
        ),
        Text("description:en", (Sentence("Garden", SKIPPED),)),
    )


def test_unsplit_text_is_one_sentence():
    ruin = by_id(load_region(REGION).places)[2]
    assert ruin.texts == (Text("description", (Sentence("Ruin", FAILED),)),)


def test_polygon_without_labels_has_no_texts():
    forest = by_id(load_region(REGION).places)[3]
    assert forest.texts == ()


def test_missing_name_and_timestamp_fall_back():
    ruin = by_id(load_region(REGION).places)[2]
    assert ruin.name == "(unnamed)"
    assert ruin.timestamp == ""


def test_timestamp_and_osm_url():
    places = by_id(load_region(REGION).places)
    assert places[1].timestamp == "2024-01-02"
    assert places[1].osm_url == "https://www.openstreetmap.org/way/1"
    assert places[3].osm_url == "https://www.openstreetmap.org/relation/3"


def test_tags_become_a_dict():
    places = by_id(load_region(REGION).places)
    assert places[1].tags == {"landuse": "farmland"}
    assert places[2].tags == {}
    assert places[3].tags == {"natural": "wood"}


def test_share_yes_counts_only_yes_and_no():
    farm = by_id(load_region(REGION).places)[1]
    assert farm.count(YES) == 1
    assert farm.count(NO) == 1
    assert farm.count(SKIPPED) == 0
    assert farm.share_yes == 0.5


def test_share_yes_is_nan_without_yes_or_no():
    ruin = by_id(load_region(REGION).places)[2]
    assert math.isnan(ruin.share_yes)


def test_region_sample_counts_each_label():
    sample = load_region(REGION)
    assert sample.count(YES) == 1
    assert sample.count(NO) == 1
    assert sample.count(FAILED) == 1
    assert sample.count(SKIPPED) == 0


def test_sample_draws_that_many_places_reproducibly():
    first = load_region(REGION, sample_size=2)
    second = load_region(REGION, sample_size=2)
    assert first.total == 3
    assert len(first.places) == 2
    assert [p.osm_id for p in first.places] == [p.osm_id for p in second.places]


def test_sample_with_fixed_seed_picks_known_places():
    sample = load_region(REGION, sample_size=2)
    assert [p.osm_id for p in sample.places] == [2, 3]


def test_sample_equal_to_total_keeps_order():
    sample = load_region(REGION, sample_size=3)
    assert [p.osm_id for p in sample.places] == [1, 2, 3]


def test_sample_larger_than_region_keeps_everything_in_order():
    sample = load_region(REGION, sample_size=10)
    assert [p.osm_id for p in sample.places] == [1, 2, 3]


def test_no_sample_keeps_everything_in_order():
    sample = load_region(REGION)
    assert sample.region == REGION
    assert [p.osm_id for p in sample.places] == [1, 2, 3]


def test_text_or_returns_default_for_empty_or_missing_values():
    assert _text_or("", "fallback") == "fallback"
    assert _text_or(None, "fallback") == "fallback"
    assert _text_or(3, "fallback") == "fallback"
    assert _text_or("kept", "fallback") == "kept"


def test_date_gives_iso_day_and_blank_for_missing():
    assert _date(pd.Timestamp("2024-01-02T10:00:00Z")) == "2024-01-02"
    assert _date(pd.NaT) == ""


def make_place(*texts: Text) -> Place:
    return Place(
        osm_type="way",
        osm_id=7,
        name="x",
        timestamp="",
        area_m2=1.0,
        tags={},
        geometry=shapely.box(0, 0, 1, 1),
        texts=tuple(texts),
    )


def test_shown_text_is_the_description_tag():
    farm = by_id(load_region(REGION).places)[1]
    assert farm.shown_text == farm.texts[0]
    assert by_id(load_region(REGION).places)[3].shown_text is None


def test_shown_text_falls_back_to_english_then_other_variants():
    german = Text("description:de", (Sentence("Deutsch", YES),))
    english = Text("description:en", (Sentence("English", NO),))
    assert make_place(german, english).shown_text == english
    assert make_place(german).shown_text == german


def test_shown_text_prefers_description_over_its_variants():
    local = Text("description", (Sentence("Local", YES),))
    english = Text("description:en", (Sentence("English", NO),))
    assert make_place(english, local).shown_text == local


def test_shown_text_skips_blank_variants():
    blank = Text("description", (Sentence("  ", YES),))
    english = Text("description:en", (Sentence("English", NO),))
    assert make_place(blank, english).shown_text == english


def test_no_shown_text_without_a_visible_sentence():
    assert make_place().shown_text is None
    assert make_place(Text("name", (Sentence("", YES),))).shown_text is None


def test_counts_use_only_the_shown_text_not_its_translations():
    translated = make_place(
        Text("description", (Sentence("a", YES),)),
        Text("description:en", (Sentence("b", YES), Sentence("c", NO))),
    )
    assert translated.count(YES) == 1
    assert translated.count(NO) == 0


def test_blank_sentences_are_neither_counted_nor_shown():
    spaced = make_place(Text("description", (Sentence(" ", YES), Sentence("real", NO))))
    assert spaced.count(YES) == 0
    assert spaced.count(NO) == 1
    assert [s.text for s in spaced.visible_sentences] == ["real"]
