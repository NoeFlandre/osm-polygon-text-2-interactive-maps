"""Render places as one interactive page, and as summary text and tables.

Public functions: `map_document`, `site_page`, `area_payload`, `area_json`,
`summary_table`, `stats_markdown`. The page is one HTML file. Leaflet draws
it. The page reads the data of one area at a time, either inline or from a
JSON file next to the page.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from html import escape
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
HIT_RADIUS = 6
HIT_OPACITY = 0.01
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

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Land-use map</title>
<link rel="stylesheet" href="__LEAFLET_CSS__">
<style>
html, body { margin: 0; height: 100%; }
#map { position: absolute; top: 0; right: 0; bottom: 0; left: 0; }
.leaflet-tooltip {
  white-space: normal !important; width: max-content; max-width: 320px;
  opacity: 1 !important; padding: 8px 10px; border: none; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, .2);
  font: 13px/1.4 system-ui, sans-serif; color: #0f172a;
}
.leaflet-tooltip::before { display: none; }
.lu + .lu { margin-top: 8px; }
.panel, .legend {
  position: absolute; z-index: 1000; background: #fff; border-radius: 10px;
  padding: 10px 14px; box-shadow: 0 2px 8px rgba(0, 0, 0, .2);
  font: 13px/1.4 system-ui, sans-serif; color: #0f172a;
}
.panel { top: 12px; left: 56px; width: 270px; }
.panel label { display: block; margin-top: 6px; }
.panel input[type=text], .panel input[type=search] {
  box-sizing: border-box; width: 100%; padding: 5px 7px; font: inherit;
  border: 1px solid #cbd5e1; border-radius: 6px;
}
.panel .stats { display: flex; justify-content: space-between; margin: 8px 0; }
.panel .stats b { font-size: 16px; }
.panel .status { color: #475569; min-height: 1.4em; }
.panel input[type=range] { width: 100%; margin: 4px 0 0; }
.panel.single .picker { display: none; }
.legend { bottom: 36px; right: 12px; }
.legend-title { font-weight: 600; margin-bottom: 4px; }
.legend .row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
.legend .swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
</style>
</head>
<body>
<div id="map"></div>
<div class="panel" id="panel">
  <div class="picker">
    <label for="area-search">Area</label>
    <input id="area-search" type="search" list="area-list" autocomplete="off"
           placeholder="Type an area, for example Albania">
    <datalist id="area-list"></datalist>
  </div>
  <div class="status" id="status"></div>
  <div class="stats">
    <div><b id="stat-polygons">0</b> polygons</div>
    <div><b id="stat-yes">0</b> yes labels</div>
    <div><b id="stat-no">0</b> no labels</div>
  </div>
  <label for="min-area">Smallest area shown: <b id="min-area-label">0 m²</b></label>
  <input id="min-area" type="range" min="0" max="1000" step="1" value="0">
</div>
__LEGEND__
<script src="__LEAFLET_JS__"></script>
<script>const DATA = __DATA__;</script>
<script>
(function () {
  const map = L.map("map");
  L.tileLayer(DATA.basemap.url, { maxZoom: 20, attribution: DATA.basemap.attribution }).addTo(map);
  map.setView([20, 0], 2);
  const layer = L.layerGroup().addTo(map);
  const status = document.getElementById("status");
  const slider = document.getElementById("min-area");
  const label = document.getElementById("min-area-label");
  const search = document.getElementById("area-search");
  const list = document.getElementById("area-list");
  const count = (n) => n.toLocaleString("en-US");

  let units = [];
  let maxArea = 1;
  let shownName = "";

  const thresholdFor = (value) => (Number(value) <= 0
    ? 0 : Math.pow(maxArea, Number(value) / Number(slider.max)));
  const showArea = (m2) => (m2 < 10 ? m2.toFixed(1) : count(Math.round(m2))) + " m²";

  const applyFilter = () => {
    const threshold = thresholdFor(slider.value);
    label.textContent = showArea(threshold);
    layer.clearLayers();
    let polygons = 0, yes = 0, no = 0;
    const shown = units.filter((u) => u.area >= threshold);
    // Polygons go first, so the hit markers sit on top of them.
    for (const u of shown) { layer.addLayer(u.polygon); }
    for (const u of shown) { layer.addLayer(u.marker); polygons += 1; yes += u.yes; no += u.no; }
    document.getElementById("stat-polygons").textContent = count(polygons);
    document.getElementById("stat-yes").textContent = count(yes);
    document.getElementById("stat-no").textContent = count(no);
    return { polygons, yes, no, threshold };
  };

  const makeUnit = (place) => {
    const polygon = L.geoJSON({ type: "Feature", geometry: place.polygon, properties: {} }, {
      style: { fillColor: place.color, color: place.color, weight: 1, fillOpacity: 0.5 },
    });
    const path = polygon.getLayers()[0];
    path.bindTooltip(place.tip);
    path.on("mouseover", () => path.setStyle({ weight: 3, fillOpacity: 0.75 }));
    path.on("mouseout", () => path.setStyle({ weight: 1, fillOpacity: 0.5 }));
    const marker = L.circleMarker(place.hit, {
      radius: DATA.hit.radius, stroke: false, fill: true, fillOpacity: DATA.hit.opacity,
    });
    marker.bindTooltip(place.tip);
    return { polygon, marker, area: place.area, yes: place.yes, no: place.no };
  };

  const draw = (area) => {
    units = area.places.map(makeUnit);
    maxArea = units.reduce((m, u) => Math.max(m, u.area), 1);
    shownName = area.name;
    if (area.bounds) { map.fitBounds(area.bounds); }
    applyFilter();
    status.textContent = area.name + ": " + count(area.places.length) + " of "
      + count(area.total) + " polygons" + (area.places.length < area.total ? " (sample)" : "");
  };

  const load = (entry) => {
    status.textContent = "Loading " + entry.name + "…";
    fetch(entry.file)
      .then((response) => {
        if (!response.ok) { throw new Error(String(response.status)); }
        return response.json();
      })
      .then(draw)
      .catch(() => { status.textContent = "Could not load " + entry.name + "."; });
  };

  slider.addEventListener("input", applyFilter);

  if (DATA.area) {
    document.getElementById("panel").classList.add("single");
    draw(DATA.area);
  } else {
    const byName = new Map(DATA.areas.map((entry) => [entry.name, entry]));
    for (const entry of DATA.areas) {
      const option = document.createElement("option");
      option.value = entry.name;
      list.appendChild(option);
    }
    search.addEventListener("change", () => {
      const entry = byName.get(search.value.trim());
      if (entry && entry.name !== shownName) { load(entry); }
      if (!entry) { status.textContent = "Pick an area from the list."; }
    });
    search.value = DATA.start;
    load(byName.get(DATA.start));
  }
  window.landuseApp = { map, layer, slider, thresholdFor, applyFilter, units: () => units };
})();
</script>
</body>
</html>
"""


def map_document(
    places: Sequence[Place], name: str = "polygons", total: int | None = None
) -> str:
    """Return one page that shows one area. The data is inside the page."""
    area = area_payload(name, places, len(places) if total is None else total)
    return _page({"area": area, "areas": None, "start": None})


def site_page(areas: Sequence[Mapping[str, Any]], start: str) -> str:
    """Return the site page. It lists the areas, and loads one at a time.

    Each entry holds `name`, `file` (a path next to the page), `total` and `shown`.
    `start` is the area name that the page shows first.
    """
    return _page({"area": None, "areas": list(areas), "start": start})


def area_payload(name: str, places: Sequence[Place], total: int) -> dict[str, Any]:
    """Return the JSON-ready data for one area. `total` counts all its polygons."""
    return {
        "name": name,
        "total": total,
        "bounds": _bounds(places),
        "places": [_place_record(p) for p in places],
    }


def area_json(payload: Mapping[str, Any]) -> str:
    """Return the area payload as compact JSON, for a file the page loads."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


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
        "hit": {"radius": HIT_RADIUS, "opacity": HIT_OPACITY},
        **data,
    }
    # Replace the data last. Its text must not be scanned for placeholders.
    return (
        PAGE.replace("__LEAFLET_CSS__", LEAFLET_CSS)
        .replace("__LEAFLET_JS__", LEAFLET_JS)
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
    text = json.dumps(data, ensure_ascii=False)
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
