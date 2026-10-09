"""Browser checks on the built site: hover text, colors, slider and area picker."""

import os
import threading
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from landuse_map.data import YES, load_region
from landuse_map.render import _color, _tooltip_html
from landuse_map.site import build_site, display_name

pytestmark = [pytest.mark.e2e, pytest.mark.network]

AREAS = ["albania-latest", "montenegro-latest"]

# One row per polygon unit, with its tooltip text, fill and marker position.
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
    """The tooltip text that the page should show for one polygon."""
    import re

    html = _tooltip_html(place)
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def places_of(areas):
    return [p for area in areas for p in load_region(area).places]


def test_every_polygon_and_marker_shows_text_on_hover(site_url):
    expected_places = places_of(AREAS[:1])
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            units = page.evaluate(UNITS_JS)
            assert len(units) == len(expected_places)
            assert [u for u in units if not u["text"]] == []
            # Each hover text must match the text of its own polygon.
            expected = [expected_text(q) for q in expected_places]
            assert [u["text"] for u in units] == expected
            assert Counter(u["fill"] for u in units) == Counter(
                _color(q) for q in expected_places
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
    expected = places_of(AREAS[:1])
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
        finally:
            browser.close()


def test_picking_another_area_replaces_the_polygons(site_url):
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            assert page.inner_text("#status").startswith("Albania:")
            page.fill("#area-search", display_name(AREAS[1]))
            page.dispatch_event("#area-search", "change")
            page.wait_for_function(
                "n => window.landuseApp.units().length === n",
                arg=len(places_of(AREAS[1:])),
            )
            assert page.inner_text("#status").startswith("Montenegro:")
            assert page.inner_text("#stat-polygons") == f"{len(places_of(AREAS[1:])):,}"
        finally:
            browser.close()


def test_the_picker_offers_every_area_as_a_suggestion(site_url):
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            names = page.eval_on_selector_all(
                "#area-list option", "els => els.map(e => e.value)"
            )
            assert names == sorted(display_name(a) for a in AREAS)
            assert page.locator("input[type=checkbox]").count() == 0
        finally:
            browser.close()


def test_an_unknown_area_name_gets_a_message(site_url):
    with sync_playwright() as p:
        browser, page = open_site(p, site_url)
        try:
            page.fill("#area-search", "Atlantis")
            page.dispatch_event("#area-search", "change")
            assert page.inner_text("#status") == "Pick an area from the list."
        finally:
            browser.close()
