"""Tests for the gate scripts in scripts/. They are not part of the package."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


crap = load_script("crap")
gate = load_script("mutation_gate")


def test_crap_formula_matches_the_definition():
    assert crap.Row("f", complexity=5, coverage=1.0).crap == 5
    assert crap.Row("f", complexity=5, coverage=0.0).crap == 5 + 5**2
    assert crap.Row("f", complexity=1, coverage=0.5).crap == pytest.approx(1.125)


def test_functions_lists_plain_functions_and_methods():
    source = (
        "def f():\n    return 1\n\n\nclass A:\n    def m(self):\n        return 2\n"
    )
    names = [name for name, *_ in crap.functions(source)]
    assert names == ["f", "A.m"]


def test_crap_fails_when_the_report_has_no_package_functions(tmp_path, capsys):
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {"files": {"other/x.py": {"executed_lines": [], "missing_lines": []}}}
        )
    )
    assert crap.main([str(report)]) == 2
    assert "no functions found" in capsys.readouterr().err


def test_crap_below_limit_passes_on_the_real_package(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    files = {}
    for path in (ROOT / "landuse_map").glob("*.py"):
        lines = list(range(1, path.read_text().count("\n") + 2))
        files[f"landuse_map/{path.name}"] = {
            "executed_lines": lines,
            "missing_lines": [],
        }
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": files}))
    assert crap.main([str(report), "--below", "100"]) == 0


def test_mutation_gate_passes_at_the_minimum(tmp_path):
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps({"killed": 80, "survived": 20, "total": 100}))
    assert gate.main(["--min", "80", "--stats", str(stats)]) == 0


def test_mutation_gate_fails_below_the_minimum(tmp_path):
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps({"killed": 79, "survived": 21, "total": 100}))
    assert gate.main(["--min", "80", "--stats", str(stats)]) == 1


def test_mutation_gate_fails_when_nothing_ran(tmp_path):
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps({"killed": 0, "survived": 0, "total": 0}))
    assert gate.main(["--min", "80", "--stats", str(stats)]) == 1


deploy = load_script("deploy_space")


def test_deploy_deletes_old_area_files_but_keeps_the_map(monkeypatch, tmp_path):
    calls: list[tuple[str, dict]] = []

    class FakeHub:
        def __init__(self, token: str):
            self.token = token

        def create_repo(self, **kwargs):
            calls.append(("create_repo", kwargs))

        def list_repo_files(self, **kwargs):
            return [
                "README.md",
                "index.html",
                "data/map.json",
                "data/albania-latest.json",
                "data/montenegro-latest.json",
            ]

        def delete_files(self, **kwargs):
            calls.append(("delete_files", kwargs))

        def upload_folder(self, **kwargs):
            calls.append(("upload_folder", kwargs))

    monkeypatch.setattr(deploy, "HfApi", FakeHub)
    monkeypatch.setenv("HF_TOKEN", "token")
    assert deploy.main([str(tmp_path)]) == 0
    assert [name for name, _ in calls] == [
        "create_repo",
        "delete_files",
        "upload_folder",
    ]
    deleted = calls[1][1]["delete_patterns"]
    assert deleted == ["data/albania-latest.json", "data/montenegro-latest.json"]
