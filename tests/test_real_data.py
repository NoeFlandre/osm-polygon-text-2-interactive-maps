"""Checks on the real albania data. These need Hugging Face access."""

import re

import pytest
from helpers import page_places

from landuse_map.data import load_region
from landuse_map.render import _tooltip_html, map_document

pytestmark = pytest.mark.network

ALBANIA_POLYGONS = 149
NO_DESCRIPTION_TAG = "https://www.openstreetmap.org/way/725870010"


def visible(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def test_albania_has_all_its_polygons():
    assert len(load_region("albania-latest").places) == ALBANIA_POLYGONS


def test_every_albania_polygon_has_visible_hover_text():
    for place in load_region("albania-latest").places:
        assert visible(_tooltip_html(place)), place.osm_url


def test_polygon_without_description_tag_shows_its_english_text():
    places = {p.osm_url: p for p in load_region("albania-latest").places}
    assert "paragliding takeoff" in _tooltip_html(places[NO_DESCRIPTION_TAG])


def test_albania_page_has_one_record_per_polygon():
    places = load_region("albania-latest").places
    assert len(page_places(map_document(places))) == ALBANIA_POLYGONS


REAL_AREAS = ["albania-latest", "montenegro-latest", "kosovo-latest"]


def test_real_areas_load_with_polygons():
    for area in REAL_AREAS:
        assert load_region(area).places, area
