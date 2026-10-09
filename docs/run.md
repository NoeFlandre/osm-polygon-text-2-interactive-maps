# Run locally

You need [uv](https://docs.astral.sh/uv/).

## Install

```bash
uv sync
```

## Build one map file

```bash
uv run landuse-map build albania-latest -o map.html
```

Open `map.html` in a browser.

- Add `--sample 300` to show a random sample of 300 polygons.

## Print region stats

```bash
uv run landuse-map stats albania-latest --csv table.csv
```

## Build the Space site

The site holds the five countries. Pass `--regions` to choose others.

```bash
uv run landuse-map site site-out
```

Open `site-out/index.html` in a browser.

## Check the code

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```
