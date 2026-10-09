"""Render places as one interactive map, and as summary text and tables.

Public functions: `map_document`, `summary_table`, `stats_markdown`.
"""

from __future__ import annotations

import math
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
FILL = "#0f766e"
EDGE = "#134e4a"
LABEL_TEXT = {YES: "yes", NO: "no", FAILED: "failed", SKIPPED: "not split"}
PAGE_HEAD = (
    "<title>Land-use map</title><style>html, body { margin: 0; height: 100%; }</style>"
)


def map_document(places: list[Place]) -> str:
    """Return one full-page map. Hovering a polygon shows its label and text."""
    fmap = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer(tiles=BASEMAP_URL, attr=BASEMAP_ATTR, max_zoom=20).add_to(fmap)
    for place in places:
        folium.GeoJson(
            shapely.geometry.mapping(place.geometry),
            style_function=_style,
            highlight_function=_highlight,
            tooltip=folium.Tooltip(_tooltip_html(place)),
        ).add_to(fmap)
    if places:
        minx, miny, maxx, maxy = shapely.total_bounds([p.geometry for p in places])
        fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    root = cast(folium.Figure, fmap.get_root())
    root.header.add_child(folium.Element(PAGE_HEAD))
    return root.render()


def summary_table(places: list[Place]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": p.name,
                "type": p.osm_type,
                "area_m2": round(p.area_m2),
                "sentences": sum(len(t.sentences) for t in p.texts),
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


def _style(_feature: dict) -> dict:
    return {"fillColor": FILL, "color": EDGE, "weight": 1, "fillOpacity": 0.45}


def _highlight(_feature: dict) -> dict:
    return {"weight": 3, "fillOpacity": 0.75}


def _tooltip_html(place: Place) -> str:
    body = "".join(f"<div>{line}</div>" for line in _tooltip_lines(place))
    return f'<div style="font:13px system-ui,sans-serif;max-width:340px;">{body}</div>'


def _tooltip_lines(place: Place) -> list[str]:
    landuse = place.tags.get("landuse")
    lines = [f"<b>landuse</b>: {escape(landuse)}"] if landuse else []
    if place.description is not None:
        lines.extend(_sentence_html(s) for s in place.description.sentences)
    return lines or ["no description"]


def _sentence_html(sentence: Sentence) -> str:
    label = LABEL_TEXT.get(sentence.label, sentence.label)
    return f"<b>{escape(label)}</b> {escape(sentence.text)}"


def _pct(share: float) -> str:
    return "–" if math.isnan(share) else f"{share:.0%}"
