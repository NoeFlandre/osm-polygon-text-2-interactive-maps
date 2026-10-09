# OSM land-use map

An interactive map of OpenStreetMap polygons. Each polygon shows its OSM text,
the sentences in that text, and an LLM label for each sentence: *yes* if the
sentence is relevant to land use, *no* if not.

- Pick a region (sample regions for now).
- Colour polygons by share of *yes*, or by area.
- Click a polygon for its text, tags and labels.
- The table below the map lists the same polygons with counts.

## Data

Source: [`NoeFlandre/osm-polygon-description-tag-landuse`](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse)
on Hugging Face. Labels and text are ODbL, like the OpenStreetMap input.

## Code

MIT licensed. See `LICENSE`.
