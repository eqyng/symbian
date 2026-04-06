import os
from pathlib import Path

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent

# Default: your Obsidian publish folder (adjust to your path)
SOURCE_DIR = (
    Path(
        os.environ.get(
            "OBSIDIAN_PUBLISH_DIR",
            Path.home() / "Documents" / "connect-dots" / "content" / "articles",
        )
    )
    .expanduser()
    .resolve()
)

OUT_JSON = REPO_ROOT / "data" / "articles.json"
