"""Static site: one page that shows every area of the dataset on one map.

The site runs on a free Hugging Face static Space. The page fetches one data
file, `data/map.json.gz`, with every area in it. A random sample of each area is
kept, so the file stays small enough to load in a browser.
"""

from __future__ import annotations

import gzip
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from landuse_map.data import list_areas, load_region
from landuse_map.render import area_payload, map_json, site_page

# Most polygons kept per area. Every area appears on the map.
MAX_POLYGONS_PER_AREA = 100
MAP_FILE = "data/map.json.gz"
NAME_OVERRIDES = {
    "bosnia-herzegovina": "Bosnia and Herzegovina",
    "macedonia": "North Macedonia",
}
ABBREVIATIONS = {"us", "uk"}

SPACE_README = """---
title: OSM land-use map
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: static
pinned: false
license: mit
---

Every area of the dataset is on one map. Hover over a polygon to see its land-use labels and text.
The slider hides polygons below a chosen area. The panel counts the polygons on the map.

Data: [osm-polygon-description-tag-landuse](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) (ODbL).
"""


def display_name(area: str) -> str:
    """Return an English name for an area id, for example "us-alaska-latest"."""
    slug = area.removesuffix("-latest")
    if slug in NAME_OVERRIDES:
        return NAME_OVERRIDES[slug]
    words = [
        w.upper() if w in ABBREVIATIONS else w.capitalize() for w in slug.split("-")
    ]
    return " ".join(words)


def build_site(
    out: Path,
    areas: Sequence[str] | None = None,
    sample_size: int | None = MAX_POLYGONS_PER_AREA,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Write index.html, data/map.json.gz with every area, and the Space README.

    `areas` defaults to every area in the dataset. Return the page path.
    """
    names = list(list_areas() if areas is None else areas)
    if not names:
        raise ValueError("no areas to build")
    records = [_area_record(area, sample_size, progress) for area in names]
    records.sort(key=lambda record: record["name"])
    out.mkdir(parents=True, exist_ok=True)
    (out / MAP_FILE).parent.mkdir(parents=True, exist_ok=True)
    data = map_json(records, sample_size).encode("utf-8")
    # mtime=0 keeps the file the same for the same input.
    (out / MAP_FILE).write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    page = out / "index.html"
    page.write_text(site_page(MAP_FILE), encoding="utf-8")
    (out / "README.md").write_text(SPACE_README, encoding="utf-8")
    return page


def _area_record(
    area: str,
    sample_size: int | None,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    """Load one area and return its record for the map file."""
    sample = load_region(area, sample_size=sample_size)
    name = display_name(area)
    if progress is not None:
        progress(f"{name}: {len(sample.places):,} of {sample.total:,} polygons")
    return area_payload(name, sample.places, sample.total)
