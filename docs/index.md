# OSM land-use map

This project shows OpenStreetMap polygons for five countries on one map:
Albania, Montenegro, Kosovo, North Macedonia, and Bosnia and Herzegovina.

Hover over a polygon to see:

- The label of each sentence of its `description` text. A label is *yes* if the sentence is relevant for land use, and *no* if it is not.
- The text itself. Polygons without a `description` tag show their other description text. Polygons without any text say so.

Polygon colors show the labels:

- Teal: only yes labels.
- Orange: only no labels.
- Purple: yes and no labels.
- Grey: no yes or no label.

Use the page controls to:

- See the number of polygons shown, and the number of yes and no labels among them.
- Move the area slider to hide polygons smaller than a chosen area. The slider scale is logarithmic.
- Switch a country on or off in the layer list.

## Data

Source: [`NoeFlandre/osm-polygon-description-tag-landuse`](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) on Hugging Face. The labels and the text use the ODbL license, like the OpenStreetMap input.

## Code

The code uses the MIT license. See `LICENSE`.
