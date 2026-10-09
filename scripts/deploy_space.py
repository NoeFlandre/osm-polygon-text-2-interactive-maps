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
    api.upload_folder(
        repo_id=args.repo,
        repo_type="space",
        folder_path=args.site,
        delete_patterns=["maps/*", "style.css"],
        commit_message="chore(site): update the static site",
    )
    print(f"deployed {args.site} to https://huggingface.co/spaces/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
