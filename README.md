# OSM land-use map

This project shows OpenStreetMap polygons on one page, for every area in the dataset. Pick an area, then hover over a polygon to see its land-use labels and text.

The data comes from the Hugging Face dataset [osm-polygon-description-tag-landuse](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse). The dataset uses the ODbL license.

## Quick start

```bash
uv sync
uv run landuse-map build albania-latest -o map.html
```

Open `map.html` in a browser.

Read the full documentation with `uv run mkdocs serve`.

## License

The code uses the MIT license. See [LICENSE](LICENSE).
