# OSM land-use map

This page shows OpenStreetMap polygons. Every area of the dataset is on one map.

## Use the page

1. Open the page. Every area is on one map.
2. Hover over a polygon to see its labels and text. A label is *yes* if a sentence is relevant for land use. A label is *no* if it is not. A label is *failed* if the model answer cannot be read. A label is *not split* if the source did not split the text into sentences.
3. Use the slider to hide polygons smaller than a chosen area. The slider scale is logarithmic.
4. Read the counts. The panel shows the polygons on the map, and the yes and no labels among them.

Polygon colors:

- Teal: only yes labels.
- Orange: only no labels.
- Purple: yes and no labels.
- Grey: no yes or no label.

## Text

The hover text uses the `description` tag of the polygon. The text can be in any language. The language is the one the OSM contributor used. When a polygon has no `description` tag, the page uses another description tag.

## Limits

- This map is a sample for now. Each area shows at most 100 random polygons. The About box and the panel say how many polygons are on the map.
- The page loads one data file for all areas. While it loads, the panel shows a message and a progress bar. The counts show dashes until the map is ready.

## Data

Source: [`NoeFlandre/osm-polygon-description-tag-landuse`](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) on Hugging Face. The labels and the text use the ODbL license, like the OpenStreetMap input.

## Code

The code uses the MIT license. See `LICENSE`.
