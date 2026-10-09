"""CRAP score for each function: complexity^2 * (1 - coverage)^3 + complexity.

Complexity comes from radon (cyclomatic complexity). Coverage comes from a
coverage.py JSON report. Usage:

    uv run coverage run -m pytest
    uv run coverage json -o coverage.json
    uv run python scripts/crap.py coverage.json --below 6
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from radon.complexity import cc_visit
from radon.visitors import Function

SOURCE_DIR = "landuse_map"


@dataclass(frozen=True)
class Row:
    location: str
    complexity: int
    coverage: float

    @property
    def crap(self) -> float:
        return self.complexity**2 * (1 - self.coverage) ** 3 + self.complexity


def functions(source: str) -> Iterator[tuple[str, int, int, int]]:
    """Yield (name, first line, last line, complexity) for each function or method."""
    for block in cc_visit(source):
        if not isinstance(block, Function):
            continue
        name = f"{block.classname}.{block.name}" if block.is_method else block.name
        yield name, block.lineno, block.endline, block.complexity


def rows(report: dict, root: Path) -> list[Row]:
    result = []
    for path, data in report["files"].items():
        if not path.startswith(f"{SOURCE_DIR}/"):
            continue
        executed = set(data["executed_lines"])
        missing = set(data["missing_lines"])
        for name, first, last, complexity in functions((root / path).read_text()):
            statements = {line for line in executed | missing if first <= line <= last}
            hit = {line for line in executed if first <= line <= last}
            coverage = len(hit) / len(statements) if statements else 1.0
            result.append(Row(f"{path}:{name}", complexity, coverage))
    return sorted(result, key=lambda row: row.crap, reverse=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument(
        "--below", type=float, help="exit 1 unless every CRAP score is below N"
    )
    args = parser.parse_args(argv)

    table = rows(json.loads(args.coverage_json.read_text()), Path.cwd())
    print("| CRAP | complexity | coverage | function |")
    print("|---:|---:|---:|---|")
    for row in table:
        print(
            f"| {row.crap:.1f} | {row.complexity} | {row.coverage:.0%} | {row.location} |"
        )

    worst = table[0].crap if table else 0.0
    print(f"\n{len(table)} functions, worst CRAP {worst:.1f}")
    if args.below is not None and worst >= args.below:
        print(f"FAIL: CRAP not below {args.below:g}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
