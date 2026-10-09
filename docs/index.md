# OSM land-use map

This project shows OpenStreetMap polygons on one page. The page covers every area in the dataset.

## Use the page

1. Type an area name in the **Area** box, for example `Albania`. The box suggests names as you type.
2. The page loads the area. Its polygons appear on the map.
3. Hover over a polygon to see its labels and text. A label is *yes* if a sentence is relevant for land use. A label is *no* if it is not. A label is *failed* if the model answer cannot be read. A label is *not split* if the source did not split the text into sentences.
4. Use the slider to hide polygons smaller than a chosen area. The slider scale is logarithmic.
5. Read the counts. The panel shows the polygons on the map, and the yes and no labels among them.

Polygon colors:

- Teal: only yes labels.
- Orange: only no labels.
- Purple: yes and no labels.
- Grey: no yes or no label.

## Text

The hover text uses the `description` tag of the polygon. The text can be in any language. The language is the one the OSM contributor used. When a polygon has no `description` tag, the page uses another description tag.

## Limits

- Each area shows at most 10,000 polygons. Larger areas use a random sample. The panel says when it shows a sample.
- The page loads one area at a time. A large area can take a few seconds to load.

## Data

Source: [`NoeFlandre/osm-polygon-description-tag-landuse`](https://huggingface.co/datasets/NoeFlandre/osm-polygon-description-tag-landuse) on Hugging Face. The labels and the text use the ODbL license, like the OpenStreetMap input.

## Code

The code uses the MIT license. See `LICENSE`.
