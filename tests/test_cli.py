import csv

import pytest

from landuse_map.cli import main

REGION = "testland-latest"
FARM = "https://www.openstreetmap.org/way/1"


def test_build_writes_a_standalone_html_page(tmp_path, capsys):
    out = tmp_path / "map.html"
    assert main(["build", REGION, "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert f"wrote {out} (3 of 3 polygons)" in capsys.readouterr().out


def test_build_honours_sample_and_colour_options(tmp_path, capsys):
    out = tmp_path / "area.html"
    main(["build", REGION, "-o", str(out), "--sample", "1", "--color-by", "area_m2"])
    assert "(1 of 3 polygons)" in capsys.readouterr().out
    assert "Area" in out.read_text(encoding="utf-8")


def test_stats_prints_summary_and_table(capsys):
    assert main(["stats", REGION]) == 0
    out = capsys.readouterr().out
    assert "showing 3 of 3 polygons" in out
    assert "Farm" in out


def test_stats_writes_csv(tmp_path, capsys):
    path = tmp_path / "table.csv"
    assert main(["stats", REGION, "--csv", str(path)]) == 0
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert next(r["osm"] for r in rows) == FARM
    assert len(rows) == 3
    assert f"wrote {path}" in capsys.readouterr().out


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])
