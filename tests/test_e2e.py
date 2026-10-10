"""Browser checks on the built site: every area on one map, hover text, colors and slider."""

import os
import re
import threading
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from landuse_map.data import YES, load_region
from landuse_map.render import _color, _tooltip_html
from landuse_map.site import build_site

pytestmark = [pytest.mark.e2e, pytest.mark.network]

AREAS = ["albania-latest", "montenegro-latest"]

# One row per polygon on the map, with its tooltip text, fill and marker position.
UNITS_JS = """
() => {
  const app = window.landuseApp;
  const box = app.map.getContainer().getBoundingClientRect();
  const plain = (html) => html.replace(/<[^>]+>/g, " ").replace(/\\s+/g, " ").trim();
  return app.units().map((u) => {
    const path = u.polygon.getLayers()[0];
    const point = app.map.latLngToContainerPoint(u.marker.getLatLng());
    return {
      text: plain(String(path.getTooltip().getContent())),
      fill: path.options.fillColor,
      x: box.left + point.x,
      y: box.top + point.y,
    };
  });
}
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build_site(out, AREAS, sample_size=None)
    handler = partial(QuietHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/index.html"
    server.shutdown()


def open_site(playwright, url):
    browser = playwright.chromium.launch(
        executable_path=os.environ.get("CHROMIUM_PATH") or None,
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1300, "height": 900})
    page.goto(url, wait_until="load")
    page.wait_for_function("window.landuseApp && window.landuseApp.units().length > 0")
    return browser, page


def expected_text(place):
    """The tooltip text that the map should show for one polygon."""
    return " ".join(re.sub(r"<[^>]+>", " ", _tooltip_html(place)).split())


def places_of(areas):
    return [p for area in areas for p in load_region(area).places]


def test_every_area_is_on_one_map_without_a_picker(site_url):
    expected = places_of(AREAS)
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            assert page.locator("#area-search").count() == 0
            assert page.locator("input[type=checkbox]").count() == 0
            assert not page.is_visible("#status")
            assert len(page.evaluate("window.landuseApp.units()")) == len(expected)
            assert page.inner_text("#stat-polygons") == f"{len(expected):,}"
        finally:
            browser.close()


def test_every_polygon_and_marker_shows_text_on_hover(site_url):
    expected = places_of(AREAS)
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            units = page.evaluate(UNITS_JS)
            assert len(units) == len(expected)
            assert [u for u in units if not u["text"]] == []
            # Hit markers must stay invisible. Stacked opacity would tint the map.
            assert page.evaluate(
                "() => window.landuseApp.units().every(u => u.marker.options.fillOpacity === 0)"
            )
            assert sorted(u["text"] for u in units) == sorted(
                expected_text(q) for q in expected
            )
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


def test_slider_hides_small_polygons_and_updates_the_stats(site_url):
    expected = places_of(AREAS)
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
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
            assert (
                page.inner_text("#stat-yes") == f"{sum(q.count(YES) for q in shown):,}"
            )
            assert (
                page.inner_text("#stat-no") == f"{sum(q.count('no') for q in shown):,}"
            )
            # The map shows exactly the polygons that the stats count: one polygon and one marker each.
            layers = page.evaluate("() => window.landuseApp.layer.getLayers().length")
            assert layers == 2 * len(shown)
        finally:
            browser.close()
