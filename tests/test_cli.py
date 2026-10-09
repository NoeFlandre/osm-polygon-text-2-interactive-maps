from pathlib import Path

import pytest

from landuse_map.cli import build_parser, main
from landuse_map.site import MAX_POLYGONS

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


def test_site_writes_the_page_and_the_area_files(tmp_path, capsys):
    out = tmp_path / "site"
    assert main(["site", str(out), "--areas", REGION]) == 0
    assert (out / "index.html").exists()
    assert (out / "README.md").exists()
    assert (out / "data" / f"{REGION}.json").exists()
    assert "wrote" in capsys.readouterr().out


def test_site_sample_option_caps_each_area(tmp_path):
    import json

    out = tmp_path / "site"
    main(["site", str(out), "--areas", REGION, "--sample", "1"])
    payload = json.loads((out / "data" / f"{REGION}.json").read_text(encoding="utf-8"))
    assert len(payload["places"]) == 1


def test_site_defaults_to_every_area_and_the_cap():
    args = build_parser().parse_args(["site", "out"])
    assert args.areas is None
    assert args.sample == MAX_POLYGONS


def test_a_command_is_required():
    with pytest.raises(SystemExit):
        main([])


@pytest.mark.parametrize("value", ["-1", "0"])
def test_sample_must_be_at_least_one(value):
    with pytest.raises(SystemExit):
        main(["build", REGION, "--sample", value])


def test_unknown_area_prints_one_line_and_exits_with_2(monkeypatch, capsys):
    from helpers import not_found_error

    from landuse_map import data

    def missing(*args, **kwargs):
        raise not_found_error()

    monkeypatch.setattr(data, "hf_hub_download", missing)
    assert main(["stats", "nowhere-latest"]) == 2
    err = capsys.readouterr().err
    assert "no area named 'nowhere-latest'" in err
    assert "Traceback" not in err


def subcommand(name):
    import argparse

    parser = build_parser()
    subs = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return subs.choices[name]


@pytest.mark.parametrize(
    ("command", "text"),
    [
        ("root", "write one HTML page for one area"),
        ("root", "print region summary and table"),
        ("root", "write the static site for every area"),
        ("build", "area id, for example albania-latest"),
        ("build", "random sample of N polygons"),
        ("stats", "also write the table as a CSV file"),
        ("site", "directory for the site files"),
        ("site", "most polygons per area"),
    ],
)
def test_help_texts_are_what_users_read(command, text):
    help_text = (
        build_parser().format_help()
        if command == "root"
        else subcommand(command).format_help()
    )
    assert text in help_text
