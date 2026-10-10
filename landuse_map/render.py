"""Render places as one interactive page, and as summary text and tables.

Public functions: `map_document`, `site_page`, `area_payload`, `map_json`,
`summary_table`, `stats_markdown`. The page is one HTML file. Leaflet draws
it. The page reads the data of every area from one gzipped JSON file next to the page,
or from data inside the page.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from html import escape
from importlib import resources
from typing import Any

import pandas as pd
import shapely

from landuse_map.data import FAILED, NO, SKIPPED, YES, Place, RegionSample, Sentence

BASEMAP_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
BASEMAP_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
)
LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css"
LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"
# Subresource integrity hashes for the pinned files. A changed file fails to load.
LEAFLET_CSS_SRI = (
    "sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H"
)
LEAFLET_JS_SRI = (
    "sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH"
)
HIT_RADIUS = 6
# About 30 metres on the ground. Stored coordinates keep 1e-5 degrees (about 1 metre).
SIMPLIFY_TOLERANCE = 3e-4
COORD_DIGITS = 5
NO_TEXT_HTML = "<div>no description text</div>"
LABEL_TEXT = {YES: "yes", NO: "no", FAILED: "failed", SKIPPED: "not split"}

# Polygon color by category. The legend lists these in this order.
CATEGORY_NAME = {
    "yes": "only yes",
    "no": "only no",
    "mixed": "yes and no",
    "none": "no yes or no label",
}
CATEGORY_COLOR = {
    "yes": "#0f766e",
    "no": "#ea580c",
    "mixed": "#7c3aed",
    "none": "#94a3b8",
}

# The page template. It holds placeholders that _page fills in.
PAGE = resources.files("landuse_map").joinpath("page.html").read_text(encoding="utf-8")


def map_document(
    places: Sequence[Place], name: str = "polygons", total: int | None = None
) -> str:
    """Return one page that shows one area. The data is inside the page."""
    area = area_payload(name, places, len(places) if total is None else total)
    return _page({"areas": [area], "limit": None})


def site_page(source: str) -> str:
    """Return the site page. It fetches the map data from `source`, a path next to the page."""
    return _page({"source": source})


def area_payload(name: str, places: Sequence[Place], total: int) -> dict[str, Any]:
    """Return the JSON-ready data for one area. `total` counts all its polygons."""
    return {
        "name": name,
        "total": total,
        "bounds": _bounds(places),
        "places": [_place_record(p) for p in places],
    }


def map_json(areas: Sequence[Mapping[str, Any]], limit: int | None) -> str:
    """Return the data of every area as compact JSON. `limit` is the cap per area."""
    payload = {"limit": limit, "areas": list(areas)}
    return json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


TABLE_COLUMNS = [
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


def summary_table(places: list[Place]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": p.name,
                "type": p.osm_type,
                "area_m2": round(p.area_m2),
                "sentences": len(p.visible_sentences),
                "yes": p.count(YES),
                "no": p.count(NO),
                "failed": p.count(FAILED),
                "share_yes": None if math.isnan(p.share_yes) else round(p.share_yes, 3),
                "landuse": p.tags.get("landuse", ""),
                "osm": p.osm_url,
            }
            for p in places
        ],
        columns=TABLE_COLUMNS,
    )


def stats_markdown(sample: RegionSample) -> str:
    yes, no = sample.count(YES), sample.count(NO)
    share = yes / (yes + no) if yes + no else math.nan
    return (
        f"**{sample.region}** · showing **{len(sample.places):,}** of {sample.total:,} "
        f"polygons · {yes:,} yes · {no:,} no · share yes {_pct(share)}\n\n"
        "Labels: yes = relevant for land use · no = not relevant · "
        "failed = the answer cannot be read · not split = not split in the source data"
    )


def _page(data: dict[str, Any]) -> str:
    data = {
        "basemap": {"url": BASEMAP_URL, "attribution": BASEMAP_ATTR},
        "hit": {"radius": HIT_RADIUS},
        **data,
    }
    # Replace the data last. Its text must not be scanned for placeholders.
    return (
        PAGE.replace("__LEAFLET_CSS__", LEAFLET_CSS)
        .replace("__LEAFLET_CSS_SRI__", LEAFLET_CSS_SRI)
        .replace("__LEAFLET_JS__", LEAFLET_JS)
        .replace("__LEAFLET_JS_SRI__", LEAFLET_JS_SRI)
        .replace("__LEGEND__", _legend_html())
        .replace("__DATA__", _json_for_script(data))
    )


def _category(place: Place) -> str:
    yes, no = place.count(YES), place.count(NO)
    if yes and no:
        return "mixed"
    if yes:
        return "yes"
    if no:
        return "no"
    return "none"


def _color(place: Place) -> str:
    return CATEGORY_COLOR[_category(place)]


def _place_record(place: Place) -> dict[str, Any]:
    """Return the JSON record that the page draws for one polygon."""
    point = place.geometry.representative_point()
    return {
        "polygon": _polygon_json(place.geometry),
        "hit": [
            round(float(point.y), COORD_DIGITS),
            round(float(point.x), COORD_DIGITS),
        ],
        "color": _color(place),
        "area": round(float(place.area_m2), 2),
        "yes": place.count(YES),
        "no": place.count(NO),
        "tip": _tooltip_html(place),
    }


def _polygon_json(geometry: shapely.Geometry) -> dict[str, Any]:
    """Return a simplified GeoJSON geometry with rounded coordinates."""
    simplified = shapely.simplify(geometry, SIMPLIFY_TOLERANCE, preserve_topology=True)
    if simplified.is_empty:
        simplified = geometry
    shape = shapely.geometry.mapping(simplified)
    return {"type": shape["type"], "coordinates": _round_coords(shape["coordinates"])}


def _round_coords(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_round_coords(item) for item in value]
    return round(float(value), COORD_DIGITS)


def _bounds(places: Sequence[Place]) -> list[list[float]] | None:
    if not places:
        return None
    minx, miny, maxx, maxy = shapely.total_bounds([p.geometry for p in places])
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]


def _json_for_script(data: object) -> str:
    """Return JSON that is safe inside a script tag."""
    # allow_nan=False: a NaN or Infinity in the data stops the build.
    text = json.dumps(data, ensure_ascii=False, allow_nan=False)
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def _tooltip_html(place: Place) -> str:
    """Return the tooltip HTML for one polygon. It is never empty."""
    blocks = "".join(_sentence_block(s) for s in place.visible_sentences)
    return f"<div>{blocks}</div>" if blocks else NO_TEXT_HTML


def _sentence_block(sentence: Sentence) -> str:
    label = LABEL_TEXT.get(sentence.label, sentence.label)
    return (
        '<div class="lu">'
        f"<b>label</b>: {escape(label)}<br>"
        f"<b>text</b>: {escape(sentence.text)}"
        "</div>"
    )


def _legend_html() -> str:
    rows = "".join(
        '<div class="row">'
        f'<span class="swatch" style="background:{CATEGORY_COLOR[key]};"></span>'
        f"<span>{escape(name)}</span></div>"
        for key, name in CATEGORY_NAME.items()
    )
    return (
        f'<div class="legend"><div class="legend-title">Polygon color</div>{rows}</div>'
    )


def _pct(share: float) -> str:
    return "–" if math.isnan(share) else f"{share:.0%}"
