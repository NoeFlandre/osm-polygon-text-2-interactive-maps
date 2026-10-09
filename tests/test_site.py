import pytest

from landuse_map import site
from landuse_map.site import MAX_POLYGONS, build_site, display_name

REGION = "testland-latest"


def test_build_site_writes_the_page_one_data_file_and_the_space_readme(tmp_path):
    out = tmp_path / "site"
    page = build_site(out, [REGION], sample_size=None)

    assert page == out / "index.html"
    assert page.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert (out / "data" / f"{REGION}.json").exists()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "sdk: static" in readme
    assert "Hover over a polygon" in readme


def test_site_page_lists_the_area_by_its_english_name(tmp_path):
    out = tmp_path / "site"
    build_site(out, [REGION], sample_size=None)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '"name": "Testland"' in html
    assert '"file": "data/testland-latest.json"' in html
    assert '"start": "Testland"' in html or '"start":"Testland"' in html


def test_area_file_holds_the_capped_sample(tmp_path):
    import json

    out = tmp_path / "site"
    build_site(out, [REGION], sample_size=2)
    payload = json.loads((out / "data" / f"{REGION}.json").read_text(encoding="utf-8"))
    assert payload["name"] == "Testland"
    assert payload["total"] == 3
    assert len(payload["places"]) == 2


def test_build_site_without_areas_uses_every_area_in_the_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(site, "list_areas", lambda: [REGION])
    out = tmp_path / "site"
    build_site(out, sample_size=None)
    assert (out / "data" / f"{REGION}.json").exists()


def test_build_site_reports_progress_per_area(tmp_path):
    lines: list[str] = []
    build_site(tmp_path / "site", [REGION], sample_size=None, progress=lines.append)
    assert lines == ["Testland: 3 of 3 polygons"]


def test_build_site_refuses_an_empty_area_list(tmp_path):
    with pytest.raises(ValueError):
        build_site(tmp_path / "site", [], sample_size=None)


def test_default_cap_keeps_large_areas_loadable():
    assert MAX_POLYGONS == 10000


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
