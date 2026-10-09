"""Load OSM polygons and their land-use sentence labels.

The Hugging Face dataset has three parquet tables for each input region:
polygons (`data/`), texts split into sentences (`language-v1/data/`), and one
label for each sentence (`labels/language-v1/data/`). This module joins the
tables. Other modules use only `load_region` and the `Place` records.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, cast

import pandas as pd
import pyarrow.parquet as pq
import shapely
from huggingface_hub import HfApi, hf_hub_download
from shapely.geometry.base import BaseGeometry

REPO_ID = "NoeFlandre/osm-polygon-description-tag-landuse"

YES = "yes"
NO = "no"
FAILED = "failed"
SKIPPED = "skipped_unsplit"


@dataclass(frozen=True)
class Sentence:
    text: str
    label: str  # YES, NO, FAILED or SKIPPED


@dataclass(frozen=True)
class Text:
    tag_key: str  # "description", "description:en", ...
    sentences: tuple[Sentence, ...]


@dataclass(frozen=True)
class Place:
    osm_type: str
    osm_id: int
    name: str
    timestamp: str
    area_m2: float
    tags: dict[str, str]
    geometry: BaseGeometry
    texts: tuple[Text, ...]

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_type}/{self.osm_id}"

    def count(self, label: str) -> int:
        return sum(s.label == label for s in self.visible_sentences)

    @property
    def shown_text(self) -> Text | None:
        """The text that the map shows and counts.

        Use `description`. Otherwise use the first other description variant
        that has a non-blank sentence. Return None when no text exists.
        """
        ranked = sorted(self.texts, key=_tag_rank)
        return next((t for t in ranked if _visible_sentences(t)), None)

    @property
    def visible_sentences(self) -> tuple[Sentence, ...]:
        text = self.shown_text
        return () if text is None else _visible_sentences(text)

    @property
    def share_yes(self) -> float:
        yes, no = self.count(YES), self.count(NO)
        return yes / (yes + no) if yes + no else math.nan


@dataclass(frozen=True)
class RegionSample:
    region: str
    places: list[Place]
    total: int

    def count(self, label: str) -> int:
        return sum(p.count(label) for p in self.places)


def list_areas() -> list[str]:
    """Return the id of every area in the dataset, for example "albania-latest"."""
    entries = HfApi().list_repo_tree(REPO_ID, repo_type="dataset", path_in_repo="data")
    paths = [str(entry.path) for entry in entries]
    return sorted(PurePosixPath(p).stem for p in paths if p.endswith(".parquet"))


def load_region(region: str, sample_size: int | None = None) -> RegionSample:
    """Return the places of one input region, for example "albania-latest".

    A sample is random but seeded. The same call returns the same places.
    Nothing is cached, so a build can load many regions in turn.
    """
    places = list(_read_region(region))
    total = len(places)
    if sample_size is not None and sample_size < total:
        places = random.Random(0).sample(places, sample_size)
    return RegionSample(region=region, places=places, total=total)


def _read_region(region: str) -> tuple[Place, ...]:
    polygons = _read("data", region)
    texts = _texts_by_place(
        sources=_read("language-v1/data", region),
        labels=_read("labels/language-v1/data", region),
    )
    geometries = shapely.from_wkb(polygons["geometry"].to_numpy())
    return tuple(
        _place(row, geometry, texts.get(_place_key(row), ()))
        for row, geometry in zip(polygons.to_dict("records"), geometries, strict=True)
    )


def _texts_by_place(
    sources: pd.DataFrame, labels: pd.DataFrame
) -> dict[tuple[str, int], list[Text]]:
    sources = sources.set_index("description_identity")
    texts: defaultdict[tuple[str, int], list[Text]] = defaultdict(list)
    grouped = labels.sort_values("sentence_index").groupby(
        ["description_identity", "tag_key"]
    )
    for keys, rows in grouped:
        identity, tag_key = cast(tuple[str, str], keys)
        source = sources.loc[identity]
        sentences = _sentences(source, rows["decision"])
        texts[_place_key(source)].append(Text(tag_key=tag_key, sentences=sentences))
    return texts


def _sentences(source: pd.Series, decisions: pd.Series) -> tuple[Sentence, ...]:
    # An unsplit text has no sentence list. The whole text is one sentence.
    pieces = list(source["sentences"]) or [source["original_text"]]
    return tuple(
        Sentence(text=piece, label=decision)
        for piece, decision in zip(pieces, decisions, strict=False)
    )


def _place_key(row: Any) -> tuple[str, int]:
    return row["osm_type"], int(row["osm_id"])


def _place(row: Any, geometry: BaseGeometry, texts: Sequence[Text]) -> Place:
    return Place(
        osm_type=row["osm_type"],
        osm_id=int(row["osm_id"]),
        name=_text_or(row["name"], "(unnamed)"),
        timestamp=_date(row["timestamp"]),
        area_m2=float(row["area_m2"]),
        tags={tag["key"]: _text_or(tag["value"], "") for tag in row["tags"]},
        geometry=geometry,
        texts=tuple(texts),
    )


def _read(folder: str, region: str) -> pd.DataFrame:
    path = hf_hub_download(REPO_ID, f"{folder}/{region}.parquet", repo_type="dataset")
    return pq.read_table(path).to_pandas()


def _text_or(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _date(value: Any) -> str:
    return "" if pd.isna(value) else value.date().isoformat()


def _tag_rank(text: Text) -> int:
    return {"description": 0, "description:en": 1}.get(text.tag_key, 2)


def _visible_sentences(text: Text) -> tuple[Sentence, ...]:
    return tuple(s for s in text.sentences if s.text.strip())
