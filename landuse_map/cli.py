"""Command line interface. Build a page for one area, build the site, or print stats."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from landuse_map.data import load_region
from landuse_map.render import map_document, stats_markdown, summary_table
from landuse_map.site import MAX_POLYGONS, build_site, display_name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="landuse-map",
        description="Map OSM polygons with land-use labels.",  # pragma: no mutate
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser(
        "build",
        help="write one HTML page for one area",  # pragma: no mutate
    )
    build.add_argument(
        "region",
        help="area id, for example albania-latest",  # pragma: no mutate
    )
    build.add_argument("-o", "--output", type=Path, default=Path("map.html"))
    build.add_argument("--sample", type=int, help="random sample of N polygons")

    stats = commands.add_parser(
        "stats",
        help="print region summary and table",  # pragma: no mutate
    )
    stats.add_argument(
        "region",
        help="area id, for example albania-latest",  # pragma: no mutate
    )
    stats.add_argument("--sample", type=int, help="random sample of N polygons")
    stats.add_argument(
        "--csv",
        type=Path,
        help="also write the table as a CSV file",  # pragma: no mutate
    )

    site = commands.add_parser(
        "site",
        help="write the static site for every area",  # pragma: no mutate
    )
    site.add_argument(
        "output",
        type=Path,
        help="directory for the site files",  # pragma: no mutate
    )
    site.add_argument(
        "--areas",
        nargs="+",
        help="area ids to include, for example albania-latest (default: all)",  # pragma: no mutate
    )
    site.add_argument(
        "--sample",
        type=int,
        default=MAX_POLYGONS,
        help="most polygons per area",  # pragma: no mutate
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "site":
        page = build_site(args.output, args.areas, args.sample, progress=print)
        print(f"wrote {page} and the area files in {args.output / 'data'}")
        return 0

    sample = load_region(args.region, sample_size=args.sample)
    if args.command == "build":
        name = display_name(args.region)
        args.output.write_text(
            map_document(sample.places, name=name, total=sample.total), encoding="utf-8"
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
