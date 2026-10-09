"""Static site: one page with a map of several countries. Runs on a free Hugging Face static Space."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from landuse_map.data import load_region
from landuse_map.render import map_regions

SITE_NAMES = {
    "albania-latest": "Albania",
    "montenegro-latest": "Montenegro",
    "kosovo-latest": "Kosovo",
    "macedonia-latest": "North Macedonia",
    "bosnia-herzegovina-latest": "Bosnia and Herzegovina",
}

SPACE_README = """---
title: OSM land-use map
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: static
pinned: false
license: mit
---

Hover over a polygon to see its land-use labels and text.
Use the layer list on the map to show or hide a country.

Data: [osm-polygon-description-tag-landuse](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) (ODbL).
"""


def display_name(region: str) -> str:
    """Return the country name for a region, for example "montenegro-latest"."""
    fallback = region.removesuffix("-latest").replace("-", " ").title()
    return SITE_NAMES.get(region, fallback)


def build_site(out: Path, regions: Sequence[str] = tuple(SITE_NAMES)) -> Path:
    """Write index.html (the map) and the Space README. Return the map path."""
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"
    layers: Mapping[str, list] = {
        display_name(region): load_region(region).places for region in regions
    }
    page.write_text(map_regions(layers), encoding="utf-8")
    (out / "README.md").write_text(SPACE_README, encoding="utf-8")
    return page
