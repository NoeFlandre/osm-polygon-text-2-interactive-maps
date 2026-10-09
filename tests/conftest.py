from datetime import UTC, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import shapely

from landuse_map import data

REGION = "testland-latest"

TAGS = pa.list_(pa.struct([("key", pa.string()), ("value", pa.string())]))
POLYGONS = pa.schema(
    [
        ("osm_type", pa.string()),
        ("osm_id", pa.int64()),
        ("name", pa.string()),
        ("timestamp", pa.timestamp("ms", tz="UTC")),
        ("area_m2", pa.float64()),
        ("tags", TAGS),
        ("geometry", pa.binary()),
    ]
)
SOURCES = pa.schema(
    [
        ("description_identity", pa.string()),
        ("osm_type", pa.string()),
        ("osm_id", pa.int64()),
        ("tag_key", pa.string()),
        ("original_text", pa.string()),
        ("sentences", pa.list_(pa.string())),
    ]
)
LABELS = pa.schema(
    [
        ("description_identity", pa.string()),
        ("tag_key", pa.string()),
        ("sentence_index", pa.int32()),
        ("decision", pa.string()),
    ]
)


def _square(x: float) -> bytes:
    return shapely.to_wkb(shapely.box(x, 0, x + 1, 1))


POLYGON_ROWS = [
    {
        "osm_type": "way",
        "osm_id": 1,
        "name": "Farm",
        "timestamp": datetime(2024, 1, 2, tzinfo=UTC),
        "area_m2": 100.0,
        "tags": [{"key": "landuse", "value": "farmland"}],
        "geometry": _square(0),
    },
    {
        "osm_type": "way",
        "osm_id": 2,
        "name": None,
        "timestamp": None,
        "area_m2": 5.0,
        "tags": [],
        "geometry": _square(2),
    },
    {
        "osm_type": "relation",
        "osm_id": 3,
        "name": "Forest",
        "timestamp": datetime(2023, 5, 6, tzinfo=UTC),
        "area_m2": 50.0,
        "tags": [{"key": "natural", "value": "wood"}],
        "geometry": _square(4),
    },
]
SOURCE_ROWS = [
    {
        "description_identity": "d1",
        "osm_type": "way",
        "osm_id": 1,
        "tag_key": "description",
        "original_text": "Fields of crops. Cows graze.",
        "sentences": ["Fields of crops.", "Cows graze."],
    },
    {
        "description_identity": "d2",
        "osm_type": "way",
        "osm_id": 1,
        "tag_key": "description:en",
        "original_text": "Garden",
        "sentences": [],
    },
    {
        "description_identity": "d3",
        "osm_type": "way",
        "osm_id": 2,
        "tag_key": "description",
        "original_text": "Ruin",
        "sentences": [],
    },
]
LABEL_ROWS = [
    {
        "description_identity": "d1",
        "tag_key": "description",
        "sentence_index": 0,
        "decision": "yes",
    },
    {
        "description_identity": "d1",
        "tag_key": "description",
        "sentence_index": 1,
        "decision": "no",
    },
    {
        "description_identity": "d2",
        "tag_key": "description:en",
        "sentence_index": 0,
        "decision": "skipped_unsplit",
    },
    {
        "description_identity": "d3",
        "tag_key": "description",
        "sentence_index": 0,
        "decision": "failed",
    },
]


@pytest.fixture(autouse=True)
def region_files(tmp_path, monkeypatch):
    """Serve the three test tables in place of the Hugging Face downloads."""
    tables = {
        f"data/{REGION}.parquet": (POLYGONS, POLYGON_ROWS),
        f"language-v1/data/{REGION}.parquet": (SOURCES, SOURCE_ROWS),
        f"labels/language-v1/data/{REGION}.parquet": (LABELS, LABEL_ROWS),
    }
    paths = {}
    for filename, (schema, rows) in tables.items():
        path = tmp_path / filename.replace("/", "_")
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
        paths[filename] = str(path)

    def fake_download(repo_id: str, filename: str, repo_type: str) -> str:
        assert repo_id == data.REPO_ID
        assert repo_type == "dataset"
        return paths[filename]

    monkeypatch.setattr(data, "hf_hub_download", fake_download)
    data._read_region.cache_clear()
    yield
    data._read_region.cache_clear()
