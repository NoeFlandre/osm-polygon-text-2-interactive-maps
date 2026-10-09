"""Render places as one interactive map, and as summary text and tables.

Public functions: `map_document`, `map_regions`, `summary_table`, `stats_markdown`.
The map is one HTML page. Leaflet draws it. The page holds the data as JSON.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from html import escape

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
.panel { top: 12px; left: 56px; width: 250px; }
.panel .stats { display: flex; justify-content: space-between; margin-bottom: 8px; }
.panel .stats b { font-size: 16px; }
.panel input[type=range] { width: 100%; margin: 4px 0 0; }
.legend { bottom: 36px; right: 12px; }
.legend-title { font-weight: 600; margin-bottom: 4px; }
.legend .row { display: flex; align-items: center; gap: 8px; margin: 3px 0; }
.legend .swatch { display: inline-block; width: 14px; height: 14px; border-radius: 3px; }
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
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
  if (DATA.bounds) { map.fitBounds(DATA.bounds); } else { map.setView([20, 0], 2); }

  const units = [];
  const overlays = {};
  for (const region of DATA.regions) {
    const group = L.layerGroup();
    const regionUnits = [];
    for (const place of region.places) {
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
      regionUnits.push({
        group, polygon, path, marker, area: place.area, yes: place.yes, no: place.no,
        color: place.color, tip: place.tip, region: region.name,
      });
    }
    // Polygons first, then hit markers, so the markers sit on top.
    for (const unit of regionUnits) { group.addLayer(unit.polygon); }
    for (const unit of regionUnits) { group.addLayer(unit.marker); }
    units.push(...regionUnits);
    overlays[region.name] = group;
    group.addTo(map);
  }
  L.control.layers(null, overlays, { collapsed: false, position: "topright" }).addTo(map);

  const slider = document.getElementById("min-area");
  const label = document.getElementById("min-area-label");
  const maxArea = units.reduce((m, u) => Math.max(m, u.area), 1);
  const thresholdFor = (value) => (Number(value) <= 0
    ? 0 : Math.pow(maxArea, Number(value) / Number(slider.max)));
  const showArea = (m2) => (m2 < 10 ? m2.toFixed(1) : Math.round(m2).toLocaleString("en-US")) + " m²";

  const applyFilter = () => {
    const threshold = thresholdFor(slider.value);
    label.textContent = showArea(threshold);
    let polygons = 0, yes = 0, no = 0;
    for (const u of units) {
      const big = u.area >= threshold;
      if (big && !u.group.hasLayer(u.polygon)) { u.group.addLayer(u.polygon); }
      if (big && !u.group.hasLayer(u.marker)) { u.group.addLayer(u.marker); }
      if (!big && u.group.hasLayer(u.polygon)) { u.group.removeLayer(u.polygon); }
      if (!big && u.group.hasLayer(u.marker)) { u.group.removeLayer(u.marker); }
      if (big && map.hasLayer(u.group)) { polygons += 1; yes += u.yes; no += u.no; }
    }
    document.getElementById("stat-polygons").textContent = polygons.toLocaleString("en-US");
    document.getElementById("stat-yes").textContent = yes.toLocaleString("en-US");
    document.getElementById("stat-no").textContent = no.toLocaleString("en-US");
    return { polygons, yes, no, threshold };
  };

  slider.addEventListener("input", applyFilter);
  map.on("overlayadd overlayremove", applyFilter);
  applyFilter();
  window.landuseApp = { map, units, slider, thresholdFor, applyFilter };
})();
</script>
</body>
</html>
"""


def map_document(places: Sequence[Place]) -> str:
    """Return one full-page map of one set of places."""
    return map_regions({"polygons": places})


def map_regions(regions: Mapping[str, Sequence[Place]]) -> str:
    """Return one full-page map. Each named region is a layer the page can toggle.

    Hovering a polygon or its hit marker shows its label and text. The slider
    hides polygons below a minimum area. The stats count the polygons shown.
    """
    everything = [p for places in regions.values() for p in places]
    data = {
        "basemap": {"url": BASEMAP_URL, "attribution": BASEMAP_ATTR},
        "bounds": _bounds(everything),
        "hit": {"radius": HIT_RADIUS, "opacity": HIT_OPACITY},
        "regions": [
            {"name": name, "places": [_place_record(p) for p in places]}
            for name, places in regions.items()
        ],
    }
    # Replace the data last. Its text must not be scanned for placeholders.
    return (
        PAGE.replace("__LEAFLET_CSS__", LEAFLET_CSS)
        .replace("__LEAFLET_JS__", LEAFLET_JS)
        .replace("__LEGEND__", _legend_html())
        .replace("__DATA__", _json_for_script(data))
    )


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


def _place_record(place: Place) -> dict:
    """Return the JSON record that the page draws for one polygon."""
    point = place.geometry.representative_point()
    return {
        "polygon": shapely.geometry.mapping(place.geometry),
        "hit": [float(point.y), float(point.x)],
        "color": _color(place),
        "area": float(place.area_m2),
        "yes": place.count(YES),
        "no": place.count(NO),
        "tip": _tooltip_html(place),
    }


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
