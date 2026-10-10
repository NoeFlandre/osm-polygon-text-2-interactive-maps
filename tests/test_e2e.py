"""Browser checks on the built site: every area on one map, hover text, colors and slider."""

import os
import re
import threading
from collections import Counter
from functools import partial
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from landuse_map.data import YES, load_region
from landuse_map.render import _color, _tooltip_html
from landuse_map.site import build_site

pytestmark = [pytest.mark.e2e, pytest.mark.network]

AREAS = ["albania-latest", "montenegro-latest"]

# One row per polygon on the map, with its tooltip text, fill and hit point.
UNITS_JS = """
() => {
  const app = window.landuseApp;
  const box = app.map.getContainer().getBoundingClientRect();
  return app.units().map((u) => {
    const point = app.map.latLngToContainerPoint(u.hit);
    return {
      tip: u.tip,
      fill: u.polygon.options.fillColor,
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


def squash(html):
    """Plain text of an HTML snippet, with all whitespace removed."""
    return re.sub(r"\s+", "", unescape(re.sub(r"<[^>]+>", "", html)))


def expected_text(place):
    """The tooltip text that the map should show for one polygon."""
    return squash(_tooltip_html(place))


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
            assert page.evaluate("window.landuseApp.units().length") == len(expected)
            assert page.inner_text("#stat-polygons") == f"{len(expected):,}"
        finally:
            browser.close()


def test_every_polygon_shows_its_text_on_hover(site_url):
    expected = places_of(AREAS)
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            units = page.evaluate(UNITS_JS)
            assert len(units) == len(expected)
            assert sorted(squash(u["tip"]) for u in units) == sorted(
                expected_text(q) for q in expected
            )
            assert Counter(u["fill"] for u in units) == Counter(
                _color(q) for q in expected
            )

            allowed = {expected_text(q) for q in expected}
            silent = []
            for unit in units:
                page.mouse.move(0, 0)
                page.mouse.move(unit["x"], unit["y"])
                tip = page.locator(".leaflet-tooltip").first
                try:
                    tip.wait_for(state="visible", timeout=1500)
                    shown = squash(tip.inner_text())
                except PlaywrightTimeout:
                    shown = ""
                if shown not in allowed:
                    silent.append((unit["x"], unit["y"]))
            assert silent == [], f"{len(silent)} hit points showed no known tooltip"
        finally:
            browser.close()


def test_the_page_explains_the_map(site_url):
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            about = page.locator(".about")
            assert about.is_visible()
            text = about.inner_text()
            assert "About this map" in text
            assert "Hover over a polygon" in text
            assert about.locator("a").count() == 2
        finally:
            browser.close()


def test_a_loading_message_shows_until_the_map_is_drawn(site_url):
    expected = places_of(AREAS)
    held = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None,
            args=["--no-sandbox"],
        )
        try:
            page = browser.new_page(viewport={"width": 1300, "height": 900})
            # Hold the map file, so the loading state stays on screen.
            page.route("**/data/map.json.gz", lambda route: held.append(route))
            page.goto(site_url, wait_until="domcontentloaded")
            page.wait_for_function("() => !document.getElementById('status').hidden")
            assert page.inner_text("#status-text").startswith("Loading")
            assert page.inner_text("#stat-polygons") == "–"
            held[0].continue_()
            page.wait_for_function(
                "window.landuseApp && window.landuseApp.units().length > 0"
            )
            assert not page.is_visible("#status")
            assert page.inner_text("#stat-polygons") == f"{len(expected):,}"
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
            # The map holds exactly the polygons that the stats count.
            layers = page.evaluate("() => window.landuseApp.layer.getLayers().length")
            assert layers == len(shown)
        finally:
            browser.close()
