"""Helpers shared by the test modules."""

import json


def page_data(doc: str) -> dict:
    """Return the JSON data that a map page embeds as `const DATA`."""
    start = doc.index("const DATA = ") + len("const DATA = ")
    data, _ = json.JSONDecoder().raw_decode(doc, start)
    return data
