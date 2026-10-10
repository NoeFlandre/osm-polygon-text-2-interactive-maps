"""Upload the built site folder to a Hugging Face static Space.

Usage: uv run python scripts/deploy_space.py site-out
Needs the HF_TOKEN environment variable with write access to the Space.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from huggingface_hub import HfApi

DEFAULT_REPO = "NoeFlandre/osm-polygon-text-2-interactive-maps"
MAP_FILE = "data/map.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("site", type=Path, help="folder built by landuse-map site")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Space id, owner/name")
    args = parser.parse_args(argv)

    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(
        repo_id=args.repo,
        repo_type="space",
        space_sdk="static",
        private=False,
        exist_ok=True,
    )
    stale = stale_area_files(api, args.repo)
    if stale:
        api.delete_files(
            repo_id=args.repo,
            repo_type="space",
            delete_patterns=stale,
            commit_message="chore(site): remove the per-area data files",
        )
    api.upload_folder(
        repo_id=args.repo,
        repo_type="space",
        folder_path=args.site,
        delete_patterns=["maps/*", "style.css"],
        commit_message="chore(site): update the static site",
    )
    print(f"deployed {args.site} to https://huggingface.co/spaces/{args.repo}")
    return 0


def stale_area_files(api: HfApi, repo_id: str) -> list[str]:
    """Return the data files of earlier builds. The map file is kept."""
    files = api.list_repo_files(repo_id=repo_id, repo_type="space")
    return [
        name
        for name in files
        if name.startswith("data/") and name.endswith(".json") and name != MAP_FILE
    ]


if __name__ == "__main__":
    raise SystemExit(main())
