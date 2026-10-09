# Deploy to a Hugging Face Space

The Space runs `app.py` with Gradio. It installs `requirements.txt`, so keep it
in sync with `pyproject.toml`:

```bash
uv export --no-dev --no-hashes --no-emit-project -o requirements.txt
```

Then upload the repo files to the Space (`app.py`, `landuse_map/`,
`requirements.txt`, `README.md`). The `README.md` front matter sets the Space
SDK and entry point.
