import math

import pandas as pd

from landuse_map.data import (
    FAILED,
    NO,
    SKIPPED,
    YES,
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
    assert farm.count(SKIPPED) == 1
    assert farm.share_yes == 0.5


def test_share_yes_is_nan_without_yes_or_no():
    ruin = by_id(load_region(REGION).places)[2]
    assert math.isnan(ruin.share_yes)


def test_region_sample_counts_each_label():
    sample = load_region(REGION)
    assert sample.count(YES) == 1
    assert sample.count(NO) == 1
    assert sample.count(FAILED) == 1
    assert sample.count(SKIPPED) == 1


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


def test_description_is_the_description_tag_text():
    places = by_id(load_region(REGION).places)
    assert places[1].description == places[1].texts[0]
    assert places[2].description == Text("description", (Sentence("Ruin", FAILED),))
    assert places[3].description is None
