from pathlib import Path

import pytest

from landuse_map.cli import build_parser, main
from landuse_map.site import SITE_NAMES

REGION = "testland-latest"


def test_build_writes_one_html_page(tmp_path, capsys):
    out = tmp_path / "map.html"
    assert main(["build", REGION, "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert f"wrote {out} (3 of 3 polygons)" in capsys.readouterr().out


def test_build_uses_a_sample(tmp_path, capsys):
    out = tmp_path / "sample.html"
    main(["build", REGION, "-o", str(out), "--sample", "1"])
    assert "(1 of 3 polygons)" in capsys.readouterr().out


def test_build_defaults():
    args = build_parser().parse_args(["build", REGION])
    assert args.output == Path("map.html")
    assert args.sample is None


def test_stats_prints_summary_and_table(capsys):
    assert main(["stats", REGION]) == 0
    out = capsys.readouterr().out
    assert "showing 3 of 3 polygons" in out
    assert "Farm" in out


def test_stats_table_has_no_index_column(capsys):
    main(["stats", REGION])
    lines = capsys.readouterr().out.splitlines()
    assert any(line.split()[0] == "Farm" for line in lines if line.strip())


def test_stats_writes_csv_with_table_columns(tmp_path, capsys):
    path = tmp_path / "table.csv"
    assert main(["stats", REGION, "--csv", str(path)]) == 0
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "name,type,area_m2,sentences,yes,no,failed,share_yes,landuse,osm"
    assert len(lines) == 4
    assert f"wrote {path}" in capsys.readouterr().out


def test_stats_defaults():
    args = build_parser().parse_args(["stats", REGION])
    assert args.csv is None
    assert args.sample is None


def test_site_writes_the_space_files(tmp_path, capsys):
    out = tmp_path / "site"
    assert main(["site", str(out), "--regions", REGION]) == 0
    assert (out / "index.html").exists()
    assert (out / "README.md").exists()
    expected = f"wrote {out / 'index.html'} and {out / 'README.md'}"
    assert expected in capsys.readouterr().out


def test_site_defaults_to_the_site_regions():
    args = build_parser().parse_args(["site", "out"])
    assert args.regions == list(SITE_NAMES)


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])
