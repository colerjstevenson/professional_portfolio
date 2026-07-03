# generate_project_ui.py
"""A small Python UI to create project metadata for a portfolio website.

Features:
- Input title, description, project type, tags, YouTube link, Git link.
- File dialogs to select thumbnail, poster, and main media (images/videos).
- On submission, creates a project folder, copies selected assets, writes metadata.json.
- Generates a short (3‑second) animated WebP preview from the first video in the main media.

Dependencies:
- dearpygui (UI)
- moviepy (video processing)
- Pillow (image handling, used by moviepy)

Usage:
    python generate_project_ui.py
"""

import os
import json
import shutil
from pathlib import Path

from moviepy.video.io.VideoFileClip import VideoFileClip

import tkinter as tk
from tkinter import filedialog
import dearpygui.dearpygui as dpg

# ---------- Configuration ----------
PROJECTS_ROOT = Path.cwd() / "projects"
ASSETS_SUBDIR = "assets"
PREVIEW_DURATION = 3  # seconds for the animated WebP preview
# -----------------------------------

# Ensure the projects directory exists
PROJECTS_ROOT.mkdir(exist_ok=True)

import re

def slugify(text: str) -> str:
    """Create a filesystem‑safe slug from the project title.
    Normalizes the string, replaces spaces with hyphens, removes invalid characters,
    collapses consecutive hyphens, and strips leading/trailing hyphens."""
    # Replace spaces with hyphens and lowercase
    text = text.lower().replace(' ', '-')
    # Remove any character that is not alphanumeric or hyphen
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Collapse multiple hyphens into a single one
    text = re.sub(r'-+', '-', text)
    # Strip leading/trailing hyphens
    return text.strip('-')

def copy_file(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.copy2(src, dest)
    return dest

def generate_webp_preview(video_path: Path, output_path: Path, duration: int = PREVIEW_DURATION):
    """Generate a short animated WebP file from the first *duration* seconds of *video_path*.
    Uses moviepy which calls ffmpeg under the hood.
    """
    video = VideoFileClip(str(video_path))
    end_time = min(duration, video.duration)
    clip = video.subclipped(0, end_time) if hasattr(video, "subclipped") else video.subclip(0, end_time)
    try:
        clip.write_videofile(
            str(output_path),
            codec="libwebp",
            fps=clip.fps,
            preset="default",
            ffmpeg_params=["-loop", "0"],
            logger=None,
        )
    finally:
        clip.close()
        video.close()

def submit_callback(sender, app_data, user_data):
    title = dpg.get_value("title_input")
    description = dpg.get_value("desc_input")
    project_type = dpg.get_value("type_combo")
    tags = dpg.get_value("tags_input")
    youtube = dpg.get_value("yt_input")
    git = dpg.get_value("git_input")
    thumb_path = Path(dpg.get_value("thumb_path")) if dpg.get_value("thumb_path") else None
    poster_path = Path(dpg.get_value("poster_path")) if dpg.get_value("poster_path") else None
    featured = dpg.get_value("featured_checkbox")
    main_media_str = dpg.get_value("main_media_paths")
    main_media_paths = [Path(p) for p in main_media_str.split(";") if p]

    if not title:
        dpg.show_item("error_popup")
        return

    slug = slugify(title)
    project_dir = PROJECTS_ROOT / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = project_dir / ASSETS_SUBDIR
    assets_dir.mkdir(parents=True, exist_ok=True)

    if thumb_path and thumb_path.is_file():
        thumb_dest = assets_dir / f"thumb{thumb_path.suffix}"
        shutil.copy2(thumb_path, thumb_dest)
    if poster_path and poster_path.is_file():
        poster_dest = assets_dir / f"poster{poster_path.suffix}"
        shutil.copy2(poster_path, poster_dest)
    copied_media = []
    if len(main_media_paths) == 1:
        m = main_media_paths[0]
        if m.is_file():
            dest_name = f"main{m.suffix}"
            dest_path = assets_dir / dest_name
            shutil.copy2(m, dest_path)
            copied_media.append(dest_name)
    else:
        for idx, m in enumerate(main_media_paths, start=1):
            if m.is_file():
                dest_name = f"main.{idx:03d}{m.suffix}"
                dest_path = assets_dir / dest_name
                shutil.copy2(m, dest_path)
                copied_media.append(dest_name)
    preview_path = None
    for m in main_media_paths:
        if m.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
            preview_path = assets_dir / f"{m.stem}_preview.webp"
            generate_webp_preview(m, preview_path)
            break

    metadata = {
        "title": title,
        "description": description,
        "type": project_type,
        "tags": [t.strip() for t in tags.split(",")] if tags else [],
        "youtube": youtube,
        "git": git,
        "thumbnail": f"thumb{thumb_path.suffix}" if thumb_path else None,
        "poster": f"poster{poster_path.suffix}" if poster_path else None,
        "media": copied_media,
        "preview_webp": preview_path.name if preview_path else None,
        "featured": featured,
    }

    meta_path = project_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    # Per-project README generation removed (global README only)
    set_featured_true_for_all_projects()
    dpg.set_value("status_text", f"Project '{title}' created at {project_dir}")
    # Clear input fields after submission
    dpg.set_value("title_input", "")
    dpg.set_value("desc_input", "")
    dpg.set_value("type_combo", "film")
    dpg.set_value("tags_input", "")
    dpg.set_value("yt_input", "")
    dpg.set_value("git_input", "")
    dpg.set_value("thumb_path", "")
    dpg.set_value("poster_path", "")
    dpg.set_value("main_media_paths", "")

def set_featured_true_for_all_projects():
    """Ensure every existing project's metadata includes "featured": true.
    This is run after each project creation to back‑fill the field for older entries.
    """
    for proj_dir in PROJECTS_ROOT.iterdir():
        if proj_dir.is_dir():
            meta_path = proj_dir / "metadata.json"
            if meta_path.is_file():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                data["featured"] = True
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

def open_file_dialog(target_tag: str, multi: bool = False):
    """Open the OS file chooser and set the selected path(s) into the given DearPyGui input.

    Args:
        target_tag: The DearPyGui input tag to receive the selected path(s).
        multi: If True, allow selecting multiple files.
    """
    # Initialize a hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()
    if multi:
        files = filedialog.askopenfilenames()
        if files:
            dpg.set_value(target_tag, ";".join(files))
    else:
        file = filedialog.askopenfilename()
        if file:
            dpg.set_value(target_tag, file)
    root.destroy()

def build_ui():
    with dpg.window(label="Portfolio Project Creator", width=640, height=800, pos=[0, 0], no_move=True, no_collapse=True, no_resize=True):
        dpg.add_text("Enter project details")
        # Title
        with dpg.group(horizontal=True):
            dpg.add_text("Title")
            dpg.add_input_text(tag="title_input", width=-1)
        # Description
        with dpg.group(horizontal=True):
            dpg.add_text("Description")
            dpg.add_input_text(tag="desc_input", multiline=True, height=80, width=-1)
        # Project Type
        with dpg.group(horizontal=True):
            dpg.add_text("Project Type")
            dpg.add_combo(["film", "art", "coding"], tag="type_combo", default_value="coding", width=200)
        # Tags
        with dpg.group(horizontal=True):
            dpg.add_text("Tags (comma separated)")
            dpg.add_input_text(tag="tags_input", width=-1)
        # YouTube Link
        with dpg.group(horizontal=True):
            dpg.add_text("YouTube Link")
            dpg.add_input_text(tag="yt_input", width=-1)
        # Git Repository Link
        with dpg.group(horizontal=True):
            dpg.add_text("Git Repository Link")
            dpg.add_input_text(tag="git_input", width=-1)
        # Featured Checkbox
        dpg.add_checkbox(label="Featured Project", tag="featured_checkbox", default_value=False)
         # Thumbnail
        with dpg.group(horizontal=True):
            dpg.add_text("Thumbnail")
            dpg.add_button(label="Select Thumbnail", callback=lambda s,a,u: open_file_dialog("thumb_path"))
            dpg.add_input_text(tag="thumb_path", readonly=True, width=-1)

        # Poster
        with dpg.group(horizontal=True):
            dpg.add_text("Poster")
            dpg.add_button(label="Select Poster", callback=lambda s,a,u: open_file_dialog("poster_path"))
            dpg.add_input_text(tag="poster_path", readonly=True, width=-1)

        # Main Media
        with dpg.group(horizontal=True):
            dpg.add_text("Main Media")
            dpg.add_button(label="Select Main Media (multiple)", callback=lambda s,a,u: open_file_dialog("main_media_paths", multi=True))
            dpg.add_input_text(tag="main_media_paths", readonly=True, width=-1)

        dpg.add_spacer(height=10)
        dpg.add_button(label="Create Project", callback=submit_callback, width=-1)
        dpg.add_text("", tag="status_text")
        dpg.add_window(label="Error", modal=True, show=False, tag="error_popup", no_close=True)
        dpg.add_text("Title is required.", parent="error_popup")
        dpg.add_button(label="Close", callback=lambda: dpg.hide_item("error_popup"), parent="error_popup")

if __name__ == "__main__":
    dpg.create_context()
    dpg.create_viewport(title='Portfolio Project Creator', width=640, height=800, resizable=True)
    dpg.setup_dearpygui()
    build_ui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
