"""Browser checks. Every polygon and every hit marker must show text on hover."""

import os
from collections import Counter

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from landuse_map.data import load_region
from landuse_map.render import _color
from landuse_map.site import SITE_REGION, build_site

pytestmark = [pytest.mark.e2e, pytest.mark.network]

# Collect every layer that has a tooltip, with its text, fill and pixel position.
REPORT_JS = """
() => {
  const map = Object.getOwnPropertyNames(window)
    .map((name) => window[name])
    .find((value) => value && typeof value.latLngToContainerPoint === "function");
  const found = [];
  const isMarker = (layer) => typeof layer.getLatLng === "function";
  const collect = (layer) => {
    const groupTip = layer.eachLayer && !isMarker(layer) && layer.getTooltip && layer.getTooltip();
    if (groupTip) {
      // A GeoJSON group keeps the tooltip. Its child paths carry the colors.
      layer.eachLayer((child) => found.push({ layer: child, tip: groupTip }));
    } else if (layer.eachLayer && !isMarker(layer)) {
      layer.eachLayer(collect);
    } else if (layer.getTooltip && layer.getTooltip()) {
      found.push({ layer, tip: layer.getTooltip() });
    }
  };
  map.eachLayer(collect);
  const box = map.getContainer().getBoundingClientRect();
  return found.map(({ layer, tip }) => {
    const html = String(tip.getContent());
    const marker = isMarker(layer);
    const point = marker ? map.latLngToContainerPoint(layer.getLatLng()) : null;
    return {
      kind: marker ? "marker" : "polygon",
      text: html.replace(/<[^>]+>/g, " ").replace(/\\s+/g, " ").trim(),
      fill: layer.options.fillColor || null,
      x: point ? box.left + point.x : null,
      y: point ? box.top + point.y : null,
    };
  });
}
"""


def test_every_polygon_and_marker_shows_text_on_hover(tmp_path):
    page_file = build_site(tmp_path / "site", SITE_REGION)
    expected = load_region(SITE_REGION).places

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None,
            args=["--no-sandbox"],
        )
        try:
            page = browser.new_page(viewport={"width": 1300, "height": 900})
            page.goto(page_file.as_uri(), wait_until="load")
            page.wait_for_selector("path.leaflet-interactive", state="attached")
            layers = page.evaluate(REPORT_JS)

            polygons = [layer for layer in layers if layer["kind"] == "polygon"]
            markers = [layer for layer in layers if layer["kind"] == "marker"]
            assert len(polygons) == len(expected)
            assert len(markers) == len(expected)

            blank = [layer for layer in layers if not layer["text"]]
            assert blank == [], f"{len(blank)} layers have no tooltip text"
            assert Counter(layer["fill"] for layer in polygons) == Counter(
                _color(place) for place in expected
            )

            silent = []
            for marker in markers:
                page.mouse.move(0, 0)
                page.mouse.move(marker["x"], marker["y"])
                tip = page.locator(".leaflet-tooltip").first
                try:
                    tip.wait_for(state="visible", timeout=1500)
                    shown = tip.inner_text().strip()
                except PlaywrightTimeout:
                    shown = ""
                if not shown:
                    silent.append((marker["x"], marker["y"]))
            assert silent == [], f"{len(silent)} hit markers showed no tooltip"
        finally:
            browser.close()
