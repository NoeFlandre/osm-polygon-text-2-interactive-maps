"""Command line: write a standalone HTML map, or print a region's summary."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from landuse_map.data import load_region
from landuse_map.render import map_document, stats_markdown, summary_table

COLOR_CHOICES = ("share_yes", "area_m2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="landuse-map",
        description="Map OSM polygons with land-use sentence labels.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="write a standalone HTML map")
    build.add_argument("region", help="input region, e.g. albania-latest")
    build.add_argument("-o", "--output", type=Path, default=Path("map.html"))
    build.add_argument("--color-by", choices=COLOR_CHOICES, default="share_yes")
    build.add_argument("--sample", type=int, help="random sample of N polygons")

    stats = commands.add_parser("stats", help="print a region summary and table")
    stats.add_argument("region", help="input region, e.g. albania-latest")
    stats.add_argument("--sample", type=int, help="random sample of N polygons")
    stats.add_argument("--csv", type=Path, help="also write the table as CSV")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sample = load_region(args.region, sample_size=args.sample)
    if args.command == "build":
        args.output.write_text(
            map_document(sample.places, args.color_by), encoding="utf-8"
        )
        print(f"wrote {args.output} ({len(sample.places)} of {sample.total} polygons)")
        return 0

    table = summary_table(sample.places)
    print(stats_markdown(sample).replace("**", ""))
    print()
    print(table.to_string(index=False))
    if args.csv:
        table.to_csv(args.csv, index=False)
        print(f"wrote {args.csv}")
    return 0
