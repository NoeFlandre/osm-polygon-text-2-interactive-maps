---
title: OSM land-use map
emoji: 🗺️
colorFrom: green
colorTo: teal
sdk: gradio
sdk_version: 6.30.0
app_file: app.py
pinned: false
license: mit
---

# OSM land-use map

Interactive map of OpenStreetMap polygons with their text and land-use labels.
Data: [osm-polygon-description-tag-landuse](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) (ODbL).

Run locally: `uv sync && uv run python app.py`. Docs: `uv run mkdocs serve`.

MIT licensed, see [LICENSE](LICENSE).
