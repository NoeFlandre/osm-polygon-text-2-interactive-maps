# Run locally

Needs [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python app.py
```

Open the printed URL. The first load downloads the sample parquet files from
the Hugging Face Hub and caches them.

## Checks

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
```

## Docs

```bash
uv run mkdocs serve
```
