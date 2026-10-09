from landuse_map.site import SITE_NAMES, build_site

REGION = "testland-latest"


def test_build_site_writes_one_map_and_the_space_readme(tmp_path):
    out = tmp_path / "site"
    page = build_site(out, [REGION])

    assert page == out / "index.html"
    assert page.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "sdk: static" in readme
    assert "Hover over a polygon" in readme
    assert sorted(p.name for p in out.iterdir()) == ["README.md", "index.html"]


def test_site_lists_five_countries():
    assert len(SITE_NAMES) == 5
    assert "albania-latest" in SITE_NAMES


def test_build_site_creates_nested_folders_and_can_rerun(tmp_path):
    out = tmp_path / "a" / "b"
    build_site(out, [REGION])
    build_site(out, [REGION])
    assert (out / "index.html").exists()
