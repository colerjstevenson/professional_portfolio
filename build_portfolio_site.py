"""Build a static portfolio website from project metadata.

Usage:
    python build_portfolio_site.py

This script:
1. Scans projects/*/metadata.json
2. Normalizes project data (including the special bio schema)
3. Copies project assets into docs/project-assets/
4. Writes docs/data/projects.json used by the frontend

The generated docs/ directory is suitable for GitHub Pages hosting.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / "projects"
DOCS_DIR = ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
ASSET_OUT_DIR = DOCS_DIR / "project-assets"

PROJECT_TYPES = {"film", "art", "coding"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def to_embed_url(url: str) -> str:
    """Convert common YouTube URL formats into embeddable URLs."""
    if not url:
        return ""

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path

    if "youtu.be" in host:
        video_id = path.strip("/")
        return f"https://www.youtube.com/embed/{video_id}" if video_id else ""

    if "youtube.com" in host:
        if path.startswith("/watch"):
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            return f"https://www.youtube.com/embed/{video_id}" if video_id else ""
        if path.startswith("/shorts/"):
            video_id = path.split("/", 2)[2].strip("/")
            return f"https://www.youtube.com/embed/{video_id}" if video_id else ""
        if path.startswith("/embed/"):
            return url

    return ""


def lower_key_map(data: dict) -> dict:
    return {str(key).lower(): value for key, value in data.items()}


def copy_project_files(project_dir: Path, slug: str) -> dict:
    """Copy project files into docs/project-assets/{slug} and return URL map."""
    output_dir = ASSET_OUT_DIR / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    assets_source = project_dir / "assets"
    if assets_source.exists() and assets_source.is_dir():
        shutil.copytree(assets_source, output_dir / "assets", dirs_exist_ok=True)

    for item in project_dir.iterdir():
        if item.name == "metadata.json" or item.name == "assets":
            continue
        if item.is_file():
            shutil.copy2(item, output_dir / item.name)

    return {
        "base": f"project-assets/{slug}",
        "assets": f"project-assets/{slug}/assets",
    }


def normalize_project(project_dir: Path, raw: dict) -> dict | None:
    slug = project_dir.name
    type_value = str(raw.get("type", "")).strip().lower()
    copied_paths = copy_project_files(project_dir, slug)

    if type_value == "bio" or slug == "bio":
        by_lower = lower_key_map(raw)
        resume_file = by_lower.get("resume", "")

        image_candidates = [
            file.name
            for file in project_dir.iterdir()
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        ]
        headshot = image_candidates[0] if image_candidates else ""

        return {
            "slug": slug,
            "type": "bio",
            "name": by_lower.get("name", ""),
            "bio": by_lower.get("bio", ""),
            "headshot": f"{copied_paths['base']}/{headshot}" if headshot else "",
            "resume": f"{copied_paths['base']}/{resume_file}" if resume_file else "",
            "links": {
                "github": by_lower.get("github", ""),
                "youtube": by_lower.get("youtube", ""),
                "instagram": by_lower.get("instagram", ""),
                "demoReel": by_lower.get("demo reel", ""),
            },
        }

    if type_value not in PROJECT_TYPES:
        return None

    thumbnail = raw.get("thumbnail") or ""
    poster = raw.get("poster") or ""
    media = [item for item in (raw.get("media") or []) if item]
    preview_webp = raw.get("preview_webp") or ""
    youtube_url = str(raw.get("youtube", "") or "")

    return {
        "slug": slug,
        "type": type_value,
        "title": raw.get("title", slug.replace("-", " ").title()),
        "description": raw.get("description", ""),
        "tags": raw.get("tags", []),
        "featured": bool(raw.get("featured", False)),
        "links": {
            "youtube": youtube_url,
            "youtubeEmbed": to_embed_url(youtube_url),
            "git": str(raw.get("git", "") or ""),
        },
        "assets": {
            "base": copied_paths["base"],
            "thumbnail": f"{copied_paths['assets']}/{thumbnail}" if thumbnail else "",
            "poster": f"{copied_paths['assets']}/{poster}" if poster else "",
            "preview": f"{copied_paths['assets']}/{preview_webp}" if preview_webp else "",
            "media": [f"{copied_paths['assets']}/{name}" for name in media],
        },
    }


def build_data() -> dict:
    ensure_clean_dir(DATA_DIR)
    ensure_clean_dir(ASSET_OUT_DIR)

    projects = []
    bio = {}

    for metadata_path in sorted(PROJECTS_DIR.glob("*/metadata.json")):
        project_dir = metadata_path.parent
        raw = load_json(metadata_path)
        normalized = normalize_project(project_dir, raw)
        if not normalized:
            continue

        if normalized["type"] == "bio":
            bio = normalized
        else:
            projects.append(normalized)

    payload = {
        "bio": bio,
        "projects": projects,
    }

    with (DATA_DIR / "projects.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    return payload


def main() -> None:
    build_data()
    print("Built portfolio data into docs/data/projects.json and docs/project-assets/")


if __name__ == "__main__":
    main()