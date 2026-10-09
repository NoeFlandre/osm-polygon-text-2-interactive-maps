"""Static site: one page with one map. Runs on a free Hugging Face static Space."""

from __future__ import annotations

from pathlib import Path

from landuse_map.data import load_region
from landuse_map.render import map_document

SITE_REGION = "albania-latest"

SPACE_README = """---
title: OSM land-use map
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: static
pinned: false
license: mit
---

Hover over a polygon to see its land-use label and its text.

Data: [osm-polygon-description-tag-landuse](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) (ODbL).
"""


def build_site(out: Path, region: str = SITE_REGION) -> Path:
    """Write index.html (the map) and the Space README. Return the map path."""
    out.mkdir(parents=True, exist_ok=True)
    page = out / "index.html"
    page.write_text(map_document(load_region(region).places), encoding="utf-8")
    (out / "README.md").write_text(SPACE_README, encoding="utf-8")
    return page
