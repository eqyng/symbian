"""Build articles index from markdown files."""

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import markdown

# pip install markdown
import yaml

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent

# Default: Obsidian publish folder
SOURCE_DIR = (
    Path(
        os.environ.get(
            "OBSIDIAN_PUBLISH_DIR",
            str(Path.home() / "Documents" / "connect-dots" / "content" / "articles"),
        )
    )
    .expanduser()
    .resolve()
)

OUT_JSON = REPO_ROOT / "data" / "articles.json"

TEMPLATE_PATH = REPO_ROOT / "post-template.html"
ARTICLES_DIR = REPO_ROOT / "content" / "articles"


def _to_iso_date(value):
    """Normalize YAML date/datetime/str to 'YYYY-MM-DD'."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if len(s) >= 10 and re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    return s


def _date_label(iso_date: str) -> str:
    """e.g. '2025-03-02' -> '02 Mar '25'"""
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    return d.strftime("%d %b '%y")


def _slug_from_stem(stem: str) -> str:
    s = stem.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "post"


def _split_frontmatter(text: str):
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    if len(lines) < 2:
        return None, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, text
    yaml_text = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1 :])
    return yaml_text, body


def _load_article(path: Path) -> dict | None:
    raw = path.read_text(encoding="utf-8")
    yaml_text, _body = _split_frontmatter(raw)
    if yaml_text is None:
        print(f"skip (no YAML frontmatter): {path.name}", file=sys.stderr)
        return None
    try:
        meta = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        print(f"skip (bad YAML) {path.name}: {e}", file=sys.stderr)
        return None

    if not isinstance(meta, dict):
        print(f"skip (frontmatter not a mapping): {path.name}", file=sys.stderr)
        return None

    title = (meta.get("title") or path.stem).strip()
    iso = _to_iso_date(meta.get("date"))
    if not iso:
        print(f"skip (missing date): {path.name}", file=sys.stderr)
        return None

    slug = (meta.get("slug") or "").strip() or _slug_from_stem(path.stem)
    subheading = meta.get("subheading")
    if subheading is None:
        subheading = ""
    subheading = str(subheading).strip()

    read_time = meta.get("readTime") or meta.get("read_time") or "1 minute read"
    read_time = str(read_time).strip()

    date_label = meta.get("dateLabel") or meta.get("date_label")
    if date_label:
        date_label = str(date_label).strip()
    else:
        try:
            date_label = _date_label(iso)
        except ValueError:
            date_label = iso

    return {
        "title": title,
        "date": iso,
        "dateLabel": date_label,
        "readTime": read_time,
        "subheading": subheading,
        "slug": slug,
        "url": f"content/articles/{slug}.html",
    }


def render_html_pages(items_with_bodies: list[tuple[dict, str]]) -> None:
    """Write one HTML file per article under articles/."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    ARTICLES_DIR.mkdir(exist_ok=True)
    for item, body_md in items_with_bodies:
        body_html = markdown.markdown(body_md, extensions=["fenced_code", "tables"])
        page = (
            template.replace("{{TITLE}}", item["title"])
            .replace("{{SUBHEADING}}", item.get("subheading") or "")
            .replace("{{BODY_HTML}}", body_html)
            .replace("{{DATE_ISO}}", item["date"])
            .replace("{{DATE_LABEL}}", item["dateLabel"])
        )
        out = ARTICLES_DIR / f"{item['slug']}.html"
        out.write_text(page, encoding="utf-8")


def main():
    """Read articles from SOURCE_DIR and write to data/articles.json."""
    if not SOURCE_DIR.is_dir():
        print(f"SOURCE_DIR is not a directory: {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    items = []
    for path in sorted(SOURCE_DIR.glob("*.md")):
        item = _load_article(path)
        if item:
            items.append(item)

    items.sort(key=lambda x: x["date"], reverse=True)

    pairs: list[tuple[dict, str]] = []
    for path in sorted(SOURCE_DIR.glob("*.md")):
        item = _load_article(path)
        if not item:
            continue
        raw = path.read_text(encoding="utf-8")
        _yaml_text, body = _split_frontmatter(raw)
        pairs.append((item, body))
    pairs.sort(key=lambda x: x[0]["date"], reverse=True)
    items = [item for item, _body in pairs]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(items)} articles to {OUT_JSON}")

    render_html_pages(pairs)
    print(f"Wrote {len(pairs)} HTML files under {ARTICLES_DIR}")


if __name__ == "__main__":
    main()
