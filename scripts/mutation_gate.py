"""Fail when the mutation score is below a minimum.

Reads the stats that `mutmut export-cicd-stats` writes.
Usage: uv run python scripts/mutation_gate.py --min 75
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--min", type=float, required=True, help="minimum killed percent"
    )
    parser.add_argument(
        "--stats", type=Path, default=Path("mutants/mutmut-cicd-stats.json")
    )
    args = parser.parse_args(argv)

    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    total = stats["total"]
    score = 100 * stats["killed"] / total if total else 0.0
    print(
        f"mutation score {score:.1f}% "
        f"({stats['killed']} of {total} killed, {stats['survived']} survived)"
    )
    if score < args.min:
        print(f"FAIL: mutation score is below {args.min:g}%", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
