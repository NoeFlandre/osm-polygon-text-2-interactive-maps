"""Render places as an interactive map (folium) and as a summary table.

Public interface: `map_iframe`, `summary_table`, `stats_markdown`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from html import escape
from typing import Literal, cast

import folium
import pandas as pd
import shapely

from landuse_map.data import FAILED, NO, SKIPPED, YES, Place, RegionSample, Text

ColorBy = Literal["share_yes", "area_m2"]

# Light to dark green.
RAMP = ("#f7fcb9", "#addd8e", "#31a354", "#00441b")
NO_DATA = "#94a3b8"
BASEMAP_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
BASEMAP_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
)
KEY_TAGS = ("landuse", "natural", "leisure", "amenity", "building", "place")
_TAG_CSS = (
    "display:inline-block;background:#f1f5f9;border-radius:6px;"
    "padding:1px 6px;margin:2px 4px 2px 0;font-size:12px;"
)

# Background and text colour per sentence label.
LABEL_STYLE = {
    YES: ("#dcfce7", "#166534"),
    NO: ("#e2e8f0", "#334155"),
    FAILED: ("#fef3c7", "#92400e"),
    SKIPPED: ("#f1f5f9", "#64748b"),
}


def map_iframe(sample: RegionSample, color_by: ColorBy, height: int = 640) -> str:
    """Map embedded in an iframe, so its scripts run inside Gradio."""
    document = map_document(sample.places, color_by)
    return (
        f'<iframe srcdoc="{escape(document, quote=True)}" '
        f'style="width:100%;height:{height}px;border:0;border-radius:16px;"></iframe>'
    )


def map_document(places: list[Place], color_by: ColorBy) -> str:
    fmap = folium.Map(tiles=None, control_scale=True)
    folium.TileLayer(
        tiles=BASEMAP_URL,
        attr=BASEMAP_ATTR,
        name="Light",
        max_zoom=20,
    ).add_to(fmap)
    colour_of = _colour_scale(places, color_by)
    for place in places:
        shape = folium.GeoJson(
            shapely.geometry.mapping(place.geometry),
            style_function=_style(colour_of(place)),
            highlight_function=lambda _feature: {"weight": 3, "fillOpacity": 0.85},
            tooltip=folium.Tooltip(escape(place.name)),
        )
        shape.add_child(folium.Popup(_popup_html(place), max_width=460))
        shape.add_to(fmap)
    if places:
        minx, miny, maxx, maxy = shapely.total_bounds([p.geometry for p in places])
        fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    # Map children render inside the page's script block, so the legend goes on
    # the page root to be visible.
    root = cast(folium.Figure, fmap.get_root())
    root.html.add_child(folium.Element(_legend(color_by)))
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
    places = sample.places
    yes = sum(p.count(YES) for p in places)
    no = sum(p.count(NO) for p in places)
    share = yes / (yes + no) if yes + no else math.nan
    return (
        f"**{sample.region}** · showing **{len(places):,}** of {sample.total:,} "
        f"polygons · {yes:,} yes · {no:,} no · share yes {_pct(share)}\n\n"
        "Sentence colours: green = yes (relevant to land use) · grey = no · "
        "amber = failed (answer not parseable) · light = skipped (not split upstream)"
    )


def _colour_scale(places: list[Place], color_by: ColorBy) -> Callable[[Place], str]:
    if color_by == "share_yes":
        return lambda p: _ramp(p.share_yes)
    logs = [math.log10(p.area_m2 + 1) for p in places]
    low, high = min(logs, default=0.0), max(logs, default=1.0)
    span = (high - low) or 1.0
    return lambda p: _ramp((math.log10(p.area_m2 + 1) - low) / span)


def _style(colour: str) -> Callable[[dict], dict]:
    def style(_feature: dict) -> dict:
        return {
            "fillColor": colour,
            "color": "#1f2937",
            "weight": 1,
            "fillOpacity": 0.6,
        }

    return style


def _ramp(t: float) -> str:
    if math.isnan(t):
        return NO_DATA
    scaled = min(max(t, 0.0), 1.0) * (len(RAMP) - 1)
    i = min(int(scaled), len(RAMP) - 2)
    frac = scaled - i
    low, high = _rgb(RAMP[i]), _rgb(RAMP[i + 1])
    mixed = [round(a + (b - a) * frac) for a, b in zip(low, high, strict=True)]
    return "#" + "".join(f"{v:02x}" for v in mixed)


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _popup_html(place: Place) -> str:
    return (
        '<div style="font-family:system-ui,sans-serif;font-size:13px;'
        'line-height:1.45;color:#0f172a;">'
        f"{_header_html(place)}"
        f"{_counts_html(place)}"
        f'<div style="margin-bottom:6px;">{_key_tags_html(place)}</div>'
        f"{_texts_html(place)}</div>"
    )


def _header_html(place: Place) -> str:
    return (
        f'<div style="font-size:16px;font-weight:650;">{escape(place.name)}</div>'
        f'<div style="color:#64748b;margin:2px 0 8px;">'
        f"{escape(place.osm_type)} · {place.area_m2:,.0f} m² · "
        f"{escape(place.timestamp)} · "
        f'<a href="{escape(place.osm_url)}" target="_blank" rel="noopener">'
        "OpenStreetMap ↗</a></div>"
    )


def _counts_html(place: Place) -> str:
    return (
        f'<div style="margin-bottom:8px;">'
        f"<b>{place.count(YES)}</b> yes · <b>{place.count(NO)}</b> no · "
        f"<b>{place.count(FAILED)}</b> failed · "
        f"share yes <b>{_pct(place.share_yes)}</b></div>"
    )


def _key_tags_html(place: Place) -> str:
    tags = "".join(
        f'<span style="{_TAG_CSS}">{escape(k)}={escape(place.tags[k])}</span>'
        for k in KEY_TAGS
        if k in place.tags
    )
    return tags or '<span style="color:#64748b">no land-use tags</span>'


def _texts_html(place: Place) -> str:
    texts = "".join(_text_html(t) for t in place.texts)
    return texts or '<div style="color:#64748b">No text.</div>'


def _text_html(text: Text) -> str:
    sentences = " ".join(_sentence_html(s.text, s.label) for s in text.sentences)
    return (
        '<div style="margin-top:8px;">'
        '<div style="color:#64748b;font-size:11px;text-transform:uppercase;'
        f'letter-spacing:.04em;">{escape(text.tag_key)}</div>'
        f"<div>{sentences}</div></div>"
    )


def _sentence_html(text: str, label: str) -> str:
    background, colour = LABEL_STYLE.get(label, LABEL_STYLE[SKIPPED])
    return (
        f'<span title="{escape(label)}" style="background:{background};'
        f"color:{colour};border-radius:6px;padding:1px 5px;"
        f'display:inline-block;margin:2px 0;">{escape(text)}</span>'
    )


def _legend(color_by: ColorBy) -> str:
    if color_by == "share_yes":
        title, low, high = "Share of yes", "0%", "100%"
        no_data = (
            f'<div style="margin-top:6px;">'
            f'<span style="display:inline-block;width:10px;height:10px;'
            f'background:{NO_DATA};border-radius:2px;"></span> no text</div>'
        )
    else:
        title, low, high, no_data = "Area", "small", "large", ""
    gradient = ", ".join(RAMP)
    return (
        '<div style="position:fixed;bottom:24px;left:24px;z-index:9999;'
        "background:white;padding:10px 12px;border-radius:10px;"
        "box-shadow:0 4px 16px rgba(0,0,0,.15);"
        'font:12px system-ui,sans-serif;color:#0f172a;">'
        f'<div style="font-weight:600;margin-bottom:6px;">{title}</div>'
        f'<div style="width:180px;height:10px;border-radius:5px;'
        f'background:linear-gradient(90deg,{gradient});"></div>'
        '<div style="display:flex;justify-content:space-between;'
        f'color:#64748b;margin-top:4px;"><span>{low}</span><span>{high}</span></div>'
        f"{no_data}</div>"
    )


def _pct(share: float) -> str:
    return "–" if math.isnan(share) else f"{share:.0%}"
