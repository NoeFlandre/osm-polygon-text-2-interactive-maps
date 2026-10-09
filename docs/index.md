# OSM land-use map

This project shows OpenStreetMap polygons on one map.

Hover over a polygon to see:

- The text of its `description` tag.
- A label for each sentence of that text: *yes* if the sentence is relevant for land use, *no* if it is not.

Polygons without a `description` tag show no tooltip.

## Data

Source: [`NoeFlandre/osm-polygon-description-tag-landuse`](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) on Hugging Face. The labels and the text use the ODbL license, like the OpenStreetMap input.

## Code

The code uses the MIT license. See `LICENSE`.
