# Run locally

You need [uv](https://docs.astral.sh/uv/).

## Install

```bash
uv sync
```

## Build one page for one area

```bash
uv run landuse-map build albania-latest -o map.html
```

Open `map.html` in a browser.

- Add `--sample 300` to show a random sample of 300 polygons.

## Print area stats

```bash
uv run landuse-map stats albania-latest --csv table.csv
```

## Build the site

The site has one page and one data file. The data file holds every area.

```bash
uv run landuse-map site site-out --areas albania-latest montenegro-latest
```

Leave out `--areas` to build every area. That takes a long time, because the dataset has 386 areas.

- Add `--sample 500` to cap each area at 500 polygons. The default cap is 100.

Serve the site folder with any web server, for example `uv run python -m http.server -d site-out`. Then open the printed address. Opening `index.html` from the disk does not work, because the page loads its data file.

## Check the code

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

The browser tests need Chromium. Install it with `uv run playwright install chromium`, or set `CHROMIUM_PATH` to a Chromium binary.
