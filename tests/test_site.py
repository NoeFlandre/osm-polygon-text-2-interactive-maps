import json

import pytest

from landuse_map import site
from landuse_map.site import MAX_POLYGONS_PER_AREA, build_site, display_name

REGION = "testland-latest"


def read_map(out):
    return json.loads((out / "data" / "map.json").read_text(encoding="utf-8"))


def test_build_site_writes_the_page_the_map_file_and_the_space_readme(tmp_path):
    out = tmp_path / "site"
    page = build_site(out, [REGION], sample_size=None)

    assert page == out / "index.html"
    assert page.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert (out / "data" / "map.json").exists()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "sdk: static" in readme
    assert "Hover over a polygon" in readme


def test_the_page_fetches_the_map_file_and_has_no_area_picker(tmp_path):
    out = tmp_path / "site"
    build_site(out, [REGION], sample_size=None)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '"source": "data/map.json"' in html
    assert "area-search" not in html
    assert "area-list" not in html


def test_map_file_holds_every_area_by_its_english_name(tmp_path):
    out = tmp_path / "site"
    build_site(out, [REGION], sample_size=None)
    payload = read_map(out)
    assert [area["name"] for area in payload["areas"]] == ["Testland"]
    assert payload["areas"][0]["total"] == 3


def test_every_area_is_capped_by_the_sample(tmp_path):
    out = tmp_path / "site"
    build_site(out, [REGION], sample_size=2)
    payload = read_map(out)
    assert payload["limit"] == 2
    assert len(payload["areas"][0]["places"]) == 2
    assert payload["areas"][0]["total"] == 3


def test_build_site_without_areas_uses_every_area_in_the_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "list_areas", lambda: [REGION])
    out = tmp_path / "site"
    build_site(out, sample_size=None)
    assert [area["name"] for area in read_map(out)["areas"]] == ["Testland"]


def test_build_site_reports_progress_per_area(tmp_path):
    lines: list[str] = []
    build_site(tmp_path / "site", [REGION], sample_size=None, progress=lines.append)
    assert lines == ["Testland: 3 of 3 polygons"]


def test_build_site_refuses_an_empty_area_list(tmp_path):
    with pytest.raises(ValueError):
        build_site(tmp_path / "site", [], sample_size=None)


def test_default_cap_is_one_hundred_polygons_per_area():
    assert MAX_POLYGONS_PER_AREA == 100


@pytest.mark.parametrize(
    ("area", "name"),
    [
        ("albania-latest", "Albania"),
        ("us-alaska-latest", "US Alaska"),
        ("bosnia-herzegovina-latest", "Bosnia and Herzegovina"),
        ("macedonia-latest", "North Macedonia"),
        ("ivory-coast-latest", "Ivory Coast"),
    ],
)
def test_display_names_are_english(area, name):
    assert display_name(area) == name
