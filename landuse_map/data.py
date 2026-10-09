"""Load OSM polygons joined to their land-use sentence labels.

The Hugging Face dataset is three parquet tables per input region:
polygons (`data/`), texts split into sentences (`language-v1/data/`) and one
label per sentence (`labels/language-v1/data/`). The joins live here, so
callers only see `load_region` and the `Place` records.
"""

from __future__ import annotations

import functools
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
import pyarrow.parquet as pq
import shapely
from huggingface_hub import hf_hub_download
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
        return sum(s.label == label for t in self.texts for s in t.sentences)

    @property
    def share_yes(self) -> float:
        yes, no = self.count(YES), self.count(NO)
        return yes / (yes + no) if yes + no else math.nan


@dataclass(frozen=True)
class RegionSample:
    region: str
    places: list[Place]
    total: int


def load_region(region: str, sample_size: int | None = None) -> RegionSample:
    """Places of one input region (e.g. "albania-latest"), optionally sampled.

    The sample is random but seeded, so the same call returns the same places.
    """
    places = list(_read_region(region))
    total = len(places)
    if sample_size is not None and sample_size < total:
        places = random.Random(0).sample(places, sample_size)
    return RegionSample(region=region, places=places, total=total)


@functools.cache
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
    # Unsplit texts have no sentence list: the whole text is one sentence.
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


def _date(value: pd.Timestamp) -> str:
    return "" if pd.isna(value) else value.date().isoformat()
