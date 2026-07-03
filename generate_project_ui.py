"""Portfolio project manager and publisher.

This single script replaces the old project-creation UI and the separate site build
step with one editor that can:
- show all existing projects in ``projects/``
- edit project metadata and media
- add new projects
- remove projects
- publish the site by rebuilding ``docs/`` from the project folders
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = ROOT / "projects"
DOCS_DIR = ROOT / "docs"
DATA_DIR = DOCS_DIR / "data"
ASSET_OUT_DIR = DOCS_DIR / "project-assets"
NOJEKYLL_FILE = DOCS_DIR / ".nojekyll"

PROJECT_TYPES = ["film", "art", "coding", "bio"]
STANDARD_PROJECT_TYPES = {"film", "art", "coding"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
PREVIEW_DURATION = 3


@dataclass
class ProjectRecord:
    slug: str
    type: str
    project_dir: Path
    raw: dict
    display_name: str
    title_value: str = ""
    description_value: str = ""
    tags_value: str = ""
    youtube_value: str = ""
    git_value: str = ""
    instagram_value: str = ""
    demo_reel_value: str = ""
    featured: bool = False
    thumbnail_source: str = ""
    poster_source: str = ""
    preview_source: str = ""
    headshot_source: str = ""
    resume_source: str = ""
    media_sources: list[str] = field(default_factory=list)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    text = (text or "").strip().lower().replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def to_embed_url(url: str) -> str:
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


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def safe_text(value) -> str:
    return "" if value is None else str(value)


def safe_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def generate_webp_preview(video_path: Path, output_path: Path, duration: int = PREVIEW_DURATION) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not installed or not available on PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-t",
        str(duration),
        "-an",
        "-vcodec",
        "libwebp",
        "-loop",
        "0",
        "-preset",
        "default",
        str(output_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def copy_project_files(project_dir: Path, slug: str) -> dict:
    output_dir = ASSET_OUT_DIR / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    assets_source = project_dir / "assets"
    if assets_source.exists() and assets_source.is_dir():
        shutil.copytree(assets_source, output_dir / "assets", dirs_exist_ok=True)

    for item in project_dir.iterdir():
        if item.name in {"metadata.json", "assets"}:
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
        resume_file = safe_text(by_lower.get("resume", ""))

        image_candidates = [
            file.name
            for file in sorted(project_dir.iterdir())
            if file.is_file() and is_image_file(file)
        ]
        headshot = image_candidates[0] if image_candidates else ""

        return {
            "slug": slug,
            "type": "bio",
            "name": safe_text(by_lower.get("name", "")),
            "bio": safe_text(by_lower.get("bio", "")),
            "headshot": f"{copied_paths['base']}/{headshot}" if headshot else "",
            "resume": f"{copied_paths['base']}/{resume_file}" if resume_file else "",
            "links": {
                "github": safe_text(by_lower.get("github", "")),
                "youtube": safe_text(by_lower.get("youtube", "")),
                "instagram": safe_text(by_lower.get("instagram", "")),
                "demoReel": safe_text(by_lower.get("demo reel", "")),
            },
        }

    if type_value not in STANDARD_PROJECT_TYPES:
        return None

    thumbnail = safe_text(raw.get("thumbnail", ""))
    poster = safe_text(raw.get("poster", ""))
    media = [safe_text(item) for item in safe_list(raw.get("media", [])) if safe_text(item)]
    preview_webp = safe_text(raw.get("preview_webp", ""))
    youtube_url = safe_text(raw.get("youtube", ""))

    return {
        "slug": slug,
        "type": type_value,
        "title": safe_text(raw.get("title", slug.replace("-", " ").title())),
        "description": safe_text(raw.get("description", "")),
        "tags": safe_list(raw.get("tags", [])),
        "featured": bool(raw.get("featured", False)),
        "links": {
            "youtube": youtube_url,
            "youtubeEmbed": to_embed_url(youtube_url),
            "git": safe_text(raw.get("git", "")),
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

    NOJEKYLL_FILE.touch()
    return payload


def list_project_records() -> list[ProjectRecord]:
    records: list[ProjectRecord] = []
    if not PROJECTS_DIR.exists():
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    for metadata_path in sorted(PROJECTS_DIR.glob("*/metadata.json")):
        project_dir = metadata_path.parent
        raw = load_json(metadata_path)
        type_value = str(raw.get("type", "")).strip().lower()
        slug = project_dir.name

        if type_value == "bio" or slug == "bio":
            by_lower = lower_key_map(raw)
            headshot_source = ""
            image_candidates = [file for file in sorted(project_dir.iterdir()) if file.is_file() and is_image_file(file)]
            if image_candidates:
                headshot_source = str(image_candidates[0])

            resume_file = safe_text(by_lower.get("resume", ""))
            resume_source = str(project_dir / resume_file) if resume_file and (project_dir / resume_file).exists() else ""

            records.append(
                ProjectRecord(
                    slug=slug,
                    type="bio",
                    project_dir=project_dir,
                    raw=raw,
                    display_name=safe_text(by_lower.get("name", slug)),
                    title_value=safe_text(by_lower.get("name", "")),
                    description_value=safe_text(by_lower.get("bio", "")),
                    youtube_value=safe_text(by_lower.get("youtube", "")),
                    git_value=safe_text(by_lower.get("github", "")),
                    instagram_value=safe_text(by_lower.get("instagram", "")),
                    demo_reel_value=safe_text(by_lower.get("demo reel", "")),
                    featured=bool(raw.get("featured", False)),
                    headshot_source=headshot_source,
                    resume_source=resume_source,
                )
            )
            continue

        thumbnail = safe_text(raw.get("thumbnail", ""))
        poster = safe_text(raw.get("poster", ""))
        preview = safe_text(raw.get("preview_webp", ""))
        media = [safe_text(item) for item in safe_list(raw.get("media", [])) if safe_text(item)]

        records.append(
            ProjectRecord(
                slug=slug,
                type=type_value,
                project_dir=project_dir,
                raw=raw,
                display_name=safe_text(raw.get("title", slug.replace("-", " ").title())),
                title_value=safe_text(raw.get("title", "")),
                description_value=safe_text(raw.get("description", "")),
                tags_value=", ".join([safe_text(tag) for tag in safe_list(raw.get("tags", [])) if safe_text(tag)]),
                youtube_value=safe_text(raw.get("youtube", "")),
                git_value=safe_text(raw.get("git", "")),
                featured=bool(raw.get("featured", False)),
                thumbnail_source=str(project_dir / "assets" / thumbnail) if thumbnail else "",
                poster_source=str(project_dir / "assets" / poster) if poster else "",
                preview_source=str(project_dir / "assets" / preview) if preview else "",
                media_sources=[str(project_dir / "assets" / item) for item in media if (project_dir / "assets" / item).exists()],
            )
        )

    return records


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id = canvas.create_window((0, 0), window=self.inner, anchor="nw")

        def _sync_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        canvas.bind("<Configure>", _sync_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = canvas


class PortfolioManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Portfolio Project Manager")
        self.root.geometry("1280x900")
        self.root.minsize(1100, 760)

        self.records: list[ProjectRecord] = []
        self.records_by_slug: dict[str, ProjectRecord] = {}
        self.loaded_slug: str | None = None
        self.media_sources: list[str] = []
        self.dirty = False
        self.loading = False

        self.title_var = tk.StringVar()
        self.type_var = tk.StringVar(value="film")
        self.tags_var = tk.StringVar()
        self.youtube_var = tk.StringVar()
        self.git_var = tk.StringVar()
        self.instagram_var = tk.StringVar()
        self.demo_reel_var = tk.StringVar()
        self.thumbnail_var = tk.StringVar()
        self.poster_var = tk.StringVar()
        self.preview_var = tk.StringVar()
        self.headshot_var = tk.StringVar()
        self.resume_var = tk.StringVar()
        self.featured_var = tk.BooleanVar(value=False)
        self.slug_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Load a project or create a new one.")

        self.description_text: ScrolledText | None = None
        self.project_list: ttk.Treeview | None = None
        self.media_listbox: tk.Listbox | None = None

        self._build_layout()
        self._bind_state()
        self.refresh_project_list()
        self.new_project()

    def _build_layout(self) -> None:
        outer = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        outer.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(outer, padding=12)
        editor_frame = ttk.Frame(outer, padding=12)
        outer.add(list_frame, weight=1)
        outer.add(editor_frame, weight=4)

        ttk.Label(list_frame, text="Projects", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(list_frame, text="Select a project to edit, remove, or publish.", wraplength=280).pack(anchor="w", pady=(4, 10))

        columns = ("type", "title")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=24, selectmode="browse")
        tree.heading("type", text="Type")
        tree.heading("title", text="Title / Name")
        tree.column("type", width=70, anchor="center")
        tree.column("title", width=220, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True)
        tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.project_list = tree

        list_button_row = ttk.Frame(list_frame)
        list_button_row.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(list_button_row, text="New Project", command=self.new_project).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(list_button_row, text="Refresh", command=self.refresh_project_list).pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

        header = ttk.Frame(editor_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Project Editor", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Label(header, textvariable=self.status_var, foreground="#555").pack(side=tk.RIGHT)

        scroll = ScrollableFrame(editor_frame)
        scroll.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        form = scroll.inner

        self._build_form_sections(form)

        action_row = ttk.Frame(editor_frame)
        action_row.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(action_row, text="Save Project", command=self.save_current_project).pack(side=tk.LEFT)
        ttk.Button(action_row, text="Delete Project", command=self.delete_current_project).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(action_row, text="Publish", command=self.publish).pack(side=tk.RIGHT)

    def _build_form_sections(self, parent: ttk.Frame) -> None:
        project_box = ttk.LabelFrame(parent, text="Project Metadata", padding=12)
        project_box.pack(fill=tk.X, pady=(0, 12))

        self._entry_row(project_box, "Title / Name", self.title_var)
        self._combo_row(project_box, "Type", self.type_var, PROJECT_TYPES)
        self._text_row(project_box, "Description / Bio", height=8)
        self._entry_row(project_box, "Tags (comma separated)", self.tags_var)
        self._entry_row(project_box, "Slug", self.slug_var, readonly=True)
        ttk.Checkbutton(project_box, text="Featured Project", variable=self.featured_var, command=self.mark_dirty).pack(anchor="w", pady=(8, 0))

        links_box = ttk.LabelFrame(parent, text="Links", padding=12)
        links_box.pack(fill=tk.X, pady=(0, 12))
        self._entry_row(links_box, "YouTube", self.youtube_var)
        self._entry_row(links_box, "Git / GitHub", self.git_var)
        self._entry_row(links_box, "Instagram", self.instagram_var)
        self._entry_row(links_box, "Demo Reel", self.demo_reel_var)

        media_box = ttk.LabelFrame(parent, text="Media", padding=12)
        media_box.pack(fill=tk.X, pady=(0, 12))
        self._file_row(media_box, "Thumbnail", self.thumbnail_var, self.choose_thumbnail, self.clear_thumbnail)
        self._file_row(media_box, "Poster", self.poster_var, self.choose_poster, self.clear_poster)
        self._file_row(media_box, "Preview WebP", self.preview_var, self.choose_preview, self.clear_preview)
        self._file_row(media_box, "Headshot", self.headshot_var, self.choose_headshot, self.clear_headshot)
        self._file_row(media_box, "Resume", self.resume_var, self.choose_resume, self.clear_resume)

        media_list_box = ttk.LabelFrame(parent, text="Main Media Files", padding=12)
        media_list_box.pack(fill=tk.BOTH, expand=True)
        media_list_row = ttk.Frame(media_list_box)
        media_list_row.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(media_list_row)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        media_list = tk.Listbox(list_frame, height=10, selectmode=tk.EXTENDED)
        media_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=media_list.yview)
        media_list.configure(yscrollcommand=media_scroll.set)
        media_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        media_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.media_listbox = media_list

        media_button_col = ttk.Frame(media_list_row)
        media_button_col.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)
        ttk.Button(media_button_col, text="Add Media", command=self.add_media_files).pack(fill=tk.X)
        ttk.Button(media_button_col, text="Remove Selected", command=self.remove_selected_media).pack(fill=tk.X, pady=(8, 0))
        ttk.Button(media_button_col, text="Clear All", command=self.clear_media_files).pack(fill=tk.X, pady=(8, 0))

    def _entry_row(self, parent: ttk.Frame, label: str, variable: tk.Variable, readonly: bool = False) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT, anchor="w")
        entry = ttk.Entry(row, textvariable=variable)
        if readonly:
            entry.state(["readonly"])
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if not readonly:
            entry.bind("<KeyRelease>", lambda event: self.on_any_change())

    def _combo_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, values: list[str]) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT, anchor="w")
        combo = ttk.Combobox(row, textvariable=variable, values=values, state="readonly")
        combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        combo.bind("<<ComboboxSelected>>", lambda event: self.on_type_changed())

    def _text_row(self, parent: ttk.Frame, label: str, height: int = 6) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.BOTH, expand=True, pady=4)
        ttk.Label(row, text=label).pack(anchor="w")
        text = ScrolledText(row, height=height, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True)
        text.bind("<<Modified>>", self.on_text_modified)
        self.description_text = text

    def _file_row(self, parent: ttk.Frame, label: str, variable: tk.StringVar, choose_cmd, clear_cmd) -> None:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text=label, width=18).pack(side=tk.LEFT, anchor="w")
        ttk.Entry(row, textvariable=variable).pack(side=tk.LEFT, fill=tk.X, expand=True)
        button_row = ttk.Frame(row)
        button_row.pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(button_row, text="Choose", command=choose_cmd).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Clear", command=clear_cmd).pack(side=tk.LEFT, padx=(6, 0))

    def _bind_state(self) -> None:
        for variable in [
            self.title_var,
            self.type_var,
            self.tags_var,
            self.youtube_var,
            self.git_var,
            self.instagram_var,
            self.demo_reel_var,
            self.thumbnail_var,
            self.poster_var,
            self.preview_var,
            self.headshot_var,
            self.resume_var,
        ]:
            variable.trace_add("write", self.on_any_change)
        self.featured_var.trace_add("write", self.on_any_change)

    def mark_dirty(self, *args) -> None:
        self.on_any_change()

    def on_any_change(self, *args) -> None:
        if self.loading:
            return
        self.dirty = True
        self.update_slug_preview()
        self.status_var.set("Unsaved changes")

    def on_type_changed(self) -> None:
        self.on_any_change()

    def on_text_modified(self, event) -> None:
        if self.loading or not self.description_text:
            if self.description_text:
                self.description_text.edit_modified(False)
            return
        if self.description_text.edit_modified():
            self.dirty = True
            self.update_slug_preview()
            self.status_var.set("Unsaved changes")
            self.description_text.edit_modified(False)

    def update_slug_preview(self) -> None:
        self.slug_var.set(slugify(self.title_var.get()))

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _selected_record(self) -> ProjectRecord | None:
        if not self.project_list:
            return None
        selection = self.project_list.selection()
        if not selection:
            return None
        slug = selection[0]
        return self.records_by_slug.get(slug)

    def _current_description_text(self) -> str:
        if not self.description_text:
            return ""
        return self.description_text.get("1.0", tk.END).strip()

    def _set_description_text(self, value: str) -> None:
        if not self.description_text:
            return
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", value)
        self.description_text.edit_modified(False)

    def _set_media_list(self, media_sources: list[str]) -> None:
        if not self.media_listbox:
            return
        self.media_listbox.delete(0, tk.END)
        self.media_sources = list(media_sources)
        for source in media_sources:
            self.media_listbox.insert(tk.END, Path(source).name)

    def _maybe_save_before_switch(self) -> bool:
        if not self.dirty:
            return True
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "Save the current project before switching?",
            parent=self.root,
        )
        if result is None:
            return False
        if result:
            return self.save_current_project()
        return True

    def refresh_project_list(self, *, preserve_selection: bool = True) -> None:
        selected_slug = self.loaded_slug if preserve_selection else None
        self.records = list_project_records()
        self.records_by_slug = {record.slug: record for record in self.records}

        if not self.project_list:
            return

        self.project_list.delete(*self.project_list.get_children())
        for record in self.records:
            self.project_list.insert("", tk.END, iid=record.slug, values=(record.type, record.display_name))

        if selected_slug and selected_slug in self.records_by_slug:
            self.project_list.selection_set(selected_slug)
            self.project_list.see(selected_slug)

    def on_tree_select(self, event) -> None:
        record = self._selected_record()
        if not record:
            return
        if record.slug == self.loaded_slug:
            return
        if not self._maybe_save_before_switch():
            if self.loaded_slug and self.project_list and self.loaded_slug in self.records_by_slug:
                self.project_list.selection_set(self.loaded_slug)
            return
        self.load_record(record.slug)

    def load_record(self, slug: str) -> None:
        record = self.records_by_slug.get(slug)
        if not record:
            return

        self.loading = True
        try:
            self.loaded_slug = record.slug
            self.title_var.set(record.title_value)
            self.type_var.set(record.type)
            self.tags_var.set(record.tags_value)
            self.youtube_var.set(record.youtube_value)
            self.git_var.set(record.git_value)
            self.instagram_var.set(record.instagram_value)
            self.demo_reel_var.set(record.demo_reel_value)
            self.thumbnail_var.set(record.thumbnail_source)
            self.poster_var.set(record.poster_source)
            self.preview_var.set(record.preview_source)
            self.headshot_var.set(record.headshot_source)
            self.resume_var.set(record.resume_source)
            self.featured_var.set(record.featured)
            self._set_description_text(record.description_value)
            self._set_media_list(record.media_sources)
            self.update_slug_preview()
            self._set_status(f"Editing {record.display_name} ({record.slug})")
            self.dirty = False
        finally:
            self.loading = False

    def new_project(self) -> None:
        if not self._maybe_save_before_switch():
            return
        self.loading = True
        try:
            self.loaded_slug = None
            self.title_var.set("")
            self.type_var.set("film")
            self.tags_var.set("")
            self.youtube_var.set("")
            self.git_var.set("")
            self.instagram_var.set("")
            self.demo_reel_var.set("")
            self.thumbnail_var.set("")
            self.poster_var.set("")
            self.preview_var.set("")
            self.headshot_var.set("")
            self.resume_var.set("")
            self.featured_var.set(False)
            self._set_description_text("")
            self._set_media_list([])
            self.update_slug_preview()
            self._set_status("Creating a new project")
            self.dirty = False
            if self.project_list:
                self.project_list.selection_remove(self.project_list.selection())
        finally:
            self.loading = False

    def _choose_file(self, variable: tk.StringVar, *, multi: bool = False, filetypes=None) -> None:
        if multi:
            selected = filedialog.askopenfilenames(parent=self.root, filetypes=filetypes)
            if selected:
                self.media_sources.extend([str(Path(item)) for item in selected])
                self._set_media_list(self.media_sources)
                self.on_any_change()
            return

        selected = filedialog.askopenfilename(parent=self.root, filetypes=filetypes)
        if selected:
            variable.set(selected)

    def choose_thumbnail(self) -> None:
        self._choose_file(self.thumbnail_var, filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff"), ("All files", "*.*")])

    def choose_poster(self) -> None:
        self._choose_file(self.poster_var, filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff"), ("All files", "*.*")])

    def choose_preview(self) -> None:
        self._choose_file(self.preview_var, filetypes=[("WebP", "*.webp"), ("All files", "*.*")])

    def choose_headshot(self) -> None:
        self._choose_file(self.headshot_var, filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff"), ("All files", "*.*")])

    def choose_resume(self) -> None:
        self._choose_file(self.resume_var, filetypes=[("All files", "*.*")])

    def clear_thumbnail(self) -> None:
        self.thumbnail_var.set("")

    def clear_poster(self) -> None:
        self.poster_var.set("")

    def clear_preview(self) -> None:
        self.preview_var.set("")

    def clear_headshot(self) -> None:
        self.headshot_var.set("")

    def clear_resume(self) -> None:
        self.resume_var.set("")

    def add_media_files(self) -> None:
        selected = filedialog.askopenfilenames(
            parent=self.root,
            filetypes=[("Media files", "*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tif *.tiff *.mp4 *.mov *.avi *.mkv *.webm *.m4v"), ("All files", "*.*")],
        )
        if not selected:
            return
        self.media_sources.extend([str(Path(item)) for item in selected])
        self._set_media_list(self.media_sources)
        self.on_any_change()

    def remove_selected_media(self) -> None:
        if not self.media_listbox:
            return
        selected_indexes = list(self.media_listbox.curselection())
        if not selected_indexes:
            return
        for index in reversed(selected_indexes):
            if 0 <= index < len(self.media_sources):
                del self.media_sources[index]
        self._set_media_list(self.media_sources)
        self.on_any_change()

    def clear_media_files(self) -> None:
        self.media_sources = []
        self._set_media_list([])
        self.on_any_change()

    def _copy_selected_file(self, source_path: str, destination_path: Path) -> str:
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Missing file: {source}")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination_path)
        return destination_path.name

    def _build_standard_project(self, staging_dir: Path, title: str, slug: str) -> dict:
        assets_dir = staging_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        thumbnail = self.thumbnail_var.get().strip()
        poster = self.poster_var.get().strip()
        preview = self.preview_var.get().strip()

        metadata_media: list[str] = []
        copied_media_sources: list[Path] = []
        for source in self.media_sources:
            source_path = Path(source)
            if source_path.is_file():
                copied_media_sources.append(source_path)

        if len(copied_media_sources) == 1:
            media_source = copied_media_sources[0]
            dest_name = f"main{media_source.suffix}"
            self._copy_selected_file(str(media_source), assets_dir / dest_name)
            metadata_media.append(dest_name)
        else:
            for index, media_source in enumerate(copied_media_sources, start=1):
                dest_name = f"main.{index:03d}{media_source.suffix}"
                self._copy_selected_file(str(media_source), assets_dir / dest_name)
                metadata_media.append(dest_name)

        thumbnail_name = ""
        if thumbnail:
            thumbnail_name = self._copy_selected_file(thumbnail, assets_dir / f"thumb{Path(thumbnail).suffix}")

        poster_name = ""
        if poster:
            poster_name = self._copy_selected_file(poster, assets_dir / f"poster{Path(poster).suffix}")

        preview_name = ""
        if preview:
            preview_name = self._copy_selected_file(preview, assets_dir / f"preview{Path(preview).suffix}")
        else:
            video_source = next((source for source in copied_media_sources if is_video_file(source)), None)
            if video_source:
                preview_name = "preview.webp"
                generate_webp_preview(video_source, assets_dir / preview_name)

        return {
            "title": title,
            "description": self._current_description_text(),
            "type": self.type_var.get().strip().lower(),
            "tags": [tag.strip() for tag in self.tags_var.get().split(",") if tag.strip()],
            "youtube": self.youtube_var.get().strip(),
            "git": self.git_var.get().strip(),
            "thumbnail": thumbnail_name or None,
            "poster": poster_name or None,
            "media": metadata_media,
            "preview_webp": preview_name or None,
            "featured": bool(self.featured_var.get()),
        }

    def _build_bio_project(self, staging_dir: Path, name: str) -> dict:
        headshot = self.headshot_var.get().strip()
        resume = self.resume_var.get().strip()

        headshot_name = ""
        if headshot:
            headshot_name = self._copy_selected_file(headshot, staging_dir / f"headshot{Path(headshot).suffix}")

        resume_name = ""
        if resume:
            resume_name = self._copy_selected_file(resume, staging_dir / f"resume{Path(resume).suffix}")

        return {
            "type": "bio",
            "name": name,
            "bio": self._current_description_text(),
            "github": self.git_var.get().strip(),
            "youtube": self.youtube_var.get().strip(),
            "instagram": self.instagram_var.get().strip(),
            "demo reel": self.demo_reel_var.get().strip(),
            "resume": resume_name or None,
            "featured": bool(self.featured_var.get()),
            "headshot": headshot_name or None,
        }

    def _write_project_to_disk(self) -> str | None:
        title = self.title_var.get().strip()
        project_type = self.type_var.get().strip().lower()

        if project_type == "bio":
            if not title:
                messagebox.showerror("Missing Name", "A name is required for the bio project.", parent=self.root)
                return None
        else:
            if not title:
                messagebox.showerror("Missing Title", "A title is required.", parent=self.root)
                return None
            if project_type not in STANDARD_PROJECT_TYPES:
                messagebox.showerror("Invalid Type", "Project type must be film, art, coding, or bio.", parent=self.root)
                return None

        slug = slugify(title)
        if not slug:
            messagebox.showerror("Invalid Title", "The title does not produce a valid slug.", parent=self.root)
            return None

        if self.loaded_slug and self.loaded_slug != slug and (PROJECTS_DIR / slug).exists():
            messagebox.showerror("Slug Exists", f"Another project already uses the slug '{slug}'.", parent=self.root)
            return None

        stage_parent = PROJECTS_DIR.parent
        staging_dir = Path(tempfile.mkdtemp(prefix=f"{slug}__staging_", dir=str(stage_parent)))

        try:
            if project_type == "bio":
                metadata = self._build_bio_project(staging_dir, title)
            else:
                metadata = self._build_standard_project(staging_dir, title, slug)

            with (staging_dir / "metadata.json").open("w", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2)

            target_dir = PROJECTS_DIR / slug
            if target_dir.exists():
                shutil.rmtree(target_dir)
            staging_dir.rename(target_dir)
            self.loaded_slug = slug
            self.dirty = False
            self._set_status(f"Saved {title} to projects/{slug}")
            return slug
        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            messagebox.showerror("Save Failed", str(exc), parent=self.root)
            return None

    def save_current_project(self) -> bool:
        saved_slug = self._write_project_to_disk()
        if not saved_slug:
            return False
        self.refresh_project_list(preserve_selection=False)
        if self.project_list:
            self.project_list.selection_set(saved_slug)
            self.project_list.see(saved_slug)
        self.load_record(saved_slug)
        return True

    def delete_current_project(self) -> None:
        record = self._selected_record()
        if not record and self.loaded_slug:
            record = self.records_by_slug.get(self.loaded_slug)
        if not record:
            messagebox.showinfo("Delete Project", "Select a project first.", parent=self.root)
            return

        confirm = messagebox.askyesno(
            "Delete Project",
            f"Delete '{record.display_name}' and remove it from the site source folders?",
            parent=self.root,
        )
        if not confirm:
            return

        try:
            shutil.rmtree(record.project_dir)
        except Exception as exc:
            messagebox.showerror("Delete Failed", str(exc), parent=self.root)
            return

        self.loaded_slug = None
        self.dirty = False
        self.refresh_project_list(preserve_selection=False)
        self.new_project()
        self._set_status(f"Deleted {record.display_name}")

    def publish(self) -> None:
        if self.dirty and not self.save_current_project():
            return
        try:
            build_data()
        except Exception as exc:
            messagebox.showerror("Publish Failed", str(exc), parent=self.root)
            return
        self._set_status("Published docs/data/projects.json and docs/project-assets/")
        messagebox.showinfo("Publish Complete", "The site files have been rebuilt in docs/.", parent=self.root)


def main() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = PortfolioManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
