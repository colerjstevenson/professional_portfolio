# Portfolio Project Generator

This repository contains a **Python UI tool** that helps you create project entries for your portfolio website.

## What it does
- Collects project metadata (title, description, tags, links, etc.) via a DearPyGui interface.
- Copies selected media assets (thumbnail, poster, videos/images) into a project‑specific `assets/` folder.
- Renames assets using a consistent naming scheme:
  - Thumbnail → `thumb.<ext>`
  - Poster → `poster.<ext>`
  - Main media → `main.<ext>` (single) or `main.001.<ext>`, `main.002.<ext>` … (multiple)
- Generates a short animated WebP preview from the first video file.


## Usage
```bash
python generate_project_ui.py
```
Run the script, fill out the form, and select your media files. After submission a new folder under `projects/` will be created with:
- `metadata.json`
- Copied assets following the naming rules above
- Optional WebP preview

## Portfolio Website

The repository now includes a static website in `docs/` that is built from your `projects/` metadata.

### Build the website data
```bash
python build_portfolio_site.py
```

This command will:
- Scan all `projects/*/metadata.json` files
- Include the special `bio` project for your hero section
- Copy project files into `docs/project-assets/`
- Generate `docs/data/projects.json`

### Run locally
Use any static server from the repository root so `docs/` is served as a site. Example:
```bash
python -m http.server 8000
```
Then open:
`http://localhost:8000/docs/`

### GitHub Pages deployment
1. Push this repository to GitHub.
2. In repository settings, open **Pages**.
3. Set source to **Deploy from a branch**.
4. Select your branch and `/docs` folder.
5. Save.

The generated site includes a committed `.nojekyll` file so GitHub Pages serves the `docs/` output as plain static files instead of running it through Jekyll.

Whenever you add or edit projects, run:
```bash
python build_portfolio_site.py
```
Commit the updated `docs/data/projects.json` and `docs/project-assets/` output.

