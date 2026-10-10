"""Helpers shared by the test modules."""

import json


def page_data(doc: str) -> dict:
    """Return the JSON data that a page embeds as `const DATA`."""
    start = doc.index("const DATA = ") + len("const DATA = ")
    data, _ = json.JSONDecoder().raw_decode(doc, start)
    return data


def page_places(doc: str) -> list[dict]:
    """Return the polygon records of a page that shows one area."""
    return page_data(doc)["areas"][0]["places"]


def not_found_error():
    """Return the error that Hugging Face raises for an unknown file or area."""
    import httpx2
    from huggingface_hub.errors import RemoteEntryNotFoundError

    request = httpx2.Request("GET", "https://huggingface.co/missing")
    return RemoteEntryNotFoundError(
        "404", response=httpx2.Response(404, request=request)
    )
