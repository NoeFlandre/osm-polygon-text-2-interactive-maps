"""Hugging Face Space: interactive map of OSM polygons and their land-use labels."""

import gradio as gr

from landuse_map.data import load_region
from landuse_map.render import map_iframe, stats_markdown, summary_table

SAMPLE_REGIONS = ["albania-latest", "andorra-latest", "bermuda-latest"]
SAMPLE_SIZE = 300
COLOUR_CHOICES = {"Share of yes": "share_yes", "Area": "area_m2"}

INTRO = """# Land-use labels on OpenStreetMap polygons

Each polygon's OSM text is split into sentences. An LLM labelled each sentence
as relevant (*yes*) or not (*no*) to land use. Click a polygon for its text,
tags and labels.
"""


def update(region: str, colour_label: str):
    sample = load_region(region, sample_size=SAMPLE_SIZE)
    colour_by = COLOUR_CHOICES[colour_label]
    return (
        map_iframe(sample, colour_by),
        stats_markdown(sample),
        summary_table(sample.places),
    )


with gr.Blocks(title="Land-use map") as demo:
    gr.Markdown(INTRO)
    with gr.Row():
        region = gr.Dropdown(
            SAMPLE_REGIONS, value=SAMPLE_REGIONS[0], label="Region", scale=2
        )
        colour = gr.Radio(
            list(COLOUR_CHOICES),
            value="Share of yes",
            label="Colour polygons by",
            scale=3,
        )
    map_view = gr.HTML()
    stats = gr.Markdown()
    table = gr.Dataframe(label="Polygons", wrap=True, interactive=False)

    controls = [region, colour]
    outputs = [map_view, stats, table]
    demo.load(update, controls, outputs)
    region.change(update, controls, outputs)
    colour.change(update, controls, outputs)

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
