"""Browser checks on the built page: hover text, colors, slider and layers."""

import os
from collections import Counter

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from landuse_map.data import YES, load_region
from landuse_map.render import _color
from landuse_map.site import SITE_NAMES, build_site

pytestmark = [pytest.mark.e2e, pytest.mark.network]

# One row per polygon unit, with its tooltip text, fill and marker position.
UNITS_JS = """
() => {
  const app = window.landuseApp;
  const box = app.map.getContainer().getBoundingClientRect();
  const plain = (html) => html.replace(/<[^>]+>/g, " ").replace(/\\s+/g, " ").trim();
  return app.units.map((u) => {
    const point = app.map.latLngToContainerPoint(u.marker.getLatLng());
    return {
      text: plain(String(u.path.getTooltip().getContent())),
      fill: u.path.options.fillColor,
      x: box.left + point.x,
      y: box.top + point.y,
    };
  });
}
"""


def open_page(playwright, page_file):
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("CHROMIUM_PATH") or None,
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1300, "height": 900})
    page.goto(page_file.as_uri(), wait_until="load")
    page.wait_for_function("window.landuseApp !== undefined")
    return browser, page


def all_places():
    return [p for region in SITE_NAMES for p in load_region(region).places]


def test_every_polygon_and_marker_shows_text_on_hover(tmp_path):
    page_file = build_site(tmp_path / "site")
    expected = all_places()
    with sync_playwright() as p:
        browser, page = open_page(p, page_file)
        try:
            units = page.evaluate(UNITS_JS)
            assert len(units) == len(expected)
            assert [u for u in units if not u["text"]] == []
            assert Counter(u["fill"] for u in units) == Counter(
                _color(q) for q in expected
            )

            silent = []
            for unit in units:
                page.mouse.move(0, 0)
                page.mouse.move(unit["x"], unit["y"])
                tip = page.locator(".leaflet-tooltip").first
                try:
                    tip.wait_for(state="visible", timeout=1500)
                    shown = tip.inner_text().strip()
                except PlaywrightTimeout:
                    shown = ""
                if not shown:
                    silent.append((unit["x"], unit["y"]))
            assert silent == [], f"{len(silent)} hit markers showed no tooltip"
        finally:
            browser.close()


def test_slider_hides_small_polygons_and_updates_the_stats(tmp_path):
    page_file = build_site(tmp_path / "site")
    expected = all_places()
    with sync_playwright() as p:
        browser, page = open_page(p, page_file)
        try:
            threshold = page.evaluate("v => window.landuseApp.thresholdFor(v)", 600)
            shown = [q for q in expected if q.area_m2 >= threshold]
            assert 0 < len(shown) < len(expected)

            page.evaluate(
                """v => {
                  const s = window.landuseApp.slider;
                  s.value = v;
                  s.dispatchEvent(new Event("input"));
                }""",
                600,
            )
            assert page.inner_text("#stat-polygons") == f"{len(shown):,}"
            yes = sum(q.count(YES) for q in shown)
            assert page.inner_text("#stat-yes") == f"{yes:,}"
            assert (
                page.inner_text("#stat-no") == f"{sum(q.count('no') for q in shown):,}"
            )
            on_map = page.evaluate(
                "() => window.landuseApp.units.filter((u) => u.group.hasLayer(u.polygon)).length"
            )
            assert on_map == len(shown)
        finally:
            browser.close()


def test_switching_a_country_off_updates_the_stats(tmp_path):
    page_file = build_site(tmp_path / "site")
    first = next(iter(SITE_NAMES))
    first_count = len(load_region(first).places)
    with sync_playwright() as p:
        browser, page = open_page(p, page_file)
        try:
            total = len(all_places())
            assert page.inner_text("#stat-polygons") == f"{total:,}"
            page.click(".leaflet-control-layers-overlays input >> nth=0")
            assert page.inner_text("#stat-polygons") == f"{total - first_count:,}"
        finally:
            browser.close()
