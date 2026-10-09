"""Checks on the real albania data. These need Hugging Face access."""

import pytest

from landuse_map.data import load_region
from landuse_map.render import _tooltip_html, map_document
from landuse_map.site import SITE_REGION

pytestmark = pytest.mark.network

ALBANIA_POLYGONS = 149
NO_DESCRIPTION_TAG = "https://www.openstreetmap.org/way/725870010"


def visible(html: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", html).strip()


def test_albania_has_all_its_polygons():
    assert len(load_region(SITE_REGION).places) == ALBANIA_POLYGONS


def test_every_albania_polygon_has_visible_hover_text():
    for place in load_region(SITE_REGION).places:
        assert visible(_tooltip_html(place)), place.osm_url


def test_polygon_without_description_tag_shows_its_english_text():
    places = {p.osm_url: p for p in load_region(SITE_REGION).places}
    assert "paragliding takeoff" in _tooltip_html(places[NO_DESCRIPTION_TAG])


def test_albania_map_has_one_polygon_and_hit_marker_each():
    places = load_region(SITE_REGION).places
    doc = map_document(places)
    assert doc.count("L.geoJson(") == ALBANIA_POLYGONS
    assert doc.count("L.circleMarker(") == ALBANIA_POLYGONS
