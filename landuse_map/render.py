"""Render places as one interactive map, and as summary text and tables.

Public functions: `map_document`, `summary_table`, `stats_markdown`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from html import escape
from typing import cast

import folium
import pandas as pd
import shapely

from landuse_map.data import FAILED, NO, SKIPPED, YES, Place, RegionSample, Sentence

BASEMAP_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
BASEMAP_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
)
HIT_RADIUS = 6
HIT_OPACITY = 0.01
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
PAGE_HEAD = (
    "<title>Land-use map</title>"
    "<style>"
    "html, body { margin: 0; height: 100%; }"
    ".leaflet-tooltip {"
    " white-space: normal !important;"
    " width: max-content;"
    " max-width: 320px;"
    " opacity: 1 !important;"
    " padding: 8px 10px;"
    " border: none;"
    " border-radius: 8px;"
    " box-shadow: 0 2px 8px rgba(0, 0, 0, .2);"
    " font: 13px/1.4 system-ui, sans-serif;"
    " color: #0f172a;"
    "}"
    ".leaflet-tooltip::before { display: none; }"
    ".lu + .lu { margin-top: 8px; }"
    "</style>"
)


def map_document(places: list[Place]) -> str:
    """Return one full-page map. Hovering a polygon shows its label and text."""
    fmap = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer(tiles=BASEMAP_URL, attr=BASEMAP_ATTR, max_zoom=20).add_to(fmap)
    for place in places:
        folium.GeoJson(
            shapely.geometry.mapping(place.geometry),
            style_function=_style(_color(place)),
            highlight_function=_highlight,
            tooltip=folium.Tooltip(_tooltip_html(place)),
        ).add_to(fmap)
    # Hit markers go on top of all polygons. Each one sits at a point inside its
    # polygon, so a tiny polygon can still be hovered.
    for place in places:
        point = place.geometry.representative_point()
        folium.CircleMarker(
            location=(point.y, point.x),
            radius=HIT_RADIUS,
            stroke=False,
            fill=True,
            fill_opacity=HIT_OPACITY,
            tooltip=folium.Tooltip(_tooltip_html(place)),
        ).add_to(fmap)
    if places:
        minx, miny, maxx, maxy = shapely.total_bounds([p.geometry for p in places])
        fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    root = cast(folium.Figure, fmap.get_root())
    root.header.add_child(folium.Element(PAGE_HEAD))
    root.html.add_child(folium.Element(_legend_html()))
    return root.render()


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
        ]
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


def _style(color: str) -> Callable[[dict], dict]:
    def style(_feature: dict) -> dict:
        return {"fillColor": color, "color": color, "weight": 1, "fillOpacity": 0.5}

    return style


def _highlight(_feature: dict) -> dict:
    return {"weight": 3, "fillOpacity": 0.75}


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
        '<div style="display:flex;align-items:center;gap:8px;margin:3px 0;">'
        f'<span style="display:inline-block;width:14px;height:14px;border-radius:3px;'
        f'background:{CATEGORY_COLOR[key]};"></span>'
        f"<span>{escape(name)}</span></div>"
        for key, name in CATEGORY_NAME.items()
    )
    return (
        '<div class="legend" style="position:fixed;top:24px;right:24px;z-index:9999;'
        "background:#fff;padding:10px 12px;border-radius:10px;"
        "box-shadow:0 2px 8px rgba(0,0,0,.2);"
        'font:13px/1.4 system-ui,sans-serif;color:#0f172a;">'
        '<div style="font-weight:600;margin-bottom:4px;">Polygon color</div>'
        f"{rows}</div>"
    )


def _pct(share: float) -> str:
    return "–" if math.isnan(share) else f"{share:.0%}"
