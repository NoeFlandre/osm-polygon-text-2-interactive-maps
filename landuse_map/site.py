"""Static site: one page that shows any area of the dataset.

The site runs on a free Hugging Face static Space. The page lists every area.
It loads the data of one area at a time from a JSON file next to the page.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from landuse_map.data import list_areas, load_region
from landuse_map.render import area_json, area_payload, site_page

# Most polygons kept per area. Larger areas are sampled, and the page says so.
MAX_POLYGONS = 10000
START_AREA = "albania-latest"
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

Pick an area in the panel. Hover over a polygon to see its land-use labels and text.
The slider hides polygons below a chosen area.

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
    sample_size: int | None = MAX_POLYGONS,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Write index.html, one JSON file per area, and the Space README.

    `areas` defaults to every area in the dataset. Return the page path.
    """
    names = list(list_areas() if areas is None else areas)
    if not names:
        raise ValueError("no areas to build")
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for area in names:
        sample = load_region(area, sample_size=sample_size)
        name = display_name(area)
        payload = area_payload(name, sample.places, sample.total)
        (data_dir / f"{area}.json").write_text(area_json(payload), encoding="utf-8")
        entries.append(
            {
                "name": name,
                "file": f"data/{area}.json",
                "total": sample.total,
                "shown": len(sample.places),
            }
        )
        if progress is not None:
            progress(f"{name}: {len(sample.places):,} of {sample.total:,} polygons")

    entries.sort(key=lambda entry: entry["name"])
    start = display_name(START_AREA if START_AREA in names else names[0])
    page = out / "index.html"
    page.write_text(site_page(entries, start), encoding="utf-8")
    (out / "README.md").write_text(SPACE_README, encoding="utf-8")
    return page
