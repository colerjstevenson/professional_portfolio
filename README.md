# Portfolio Project Manager

This repository contains a **Python UI tool** that helps you manage the project entries for your portfolio website.

## What it does
- Shows every project currently in `projects/` and lets you edit or delete it.
- Creates new projects with the same metadata fields you already use.
- Lets you change thumbnails, posters, media, previews, and bio assets.
- Publishes all edits by rebuilding `docs/data/projects.json` and `docs/project-assets/`.


## Usage
```bash
python generate_project_ui.py
```
Run the script, select a project from the list, or create a new one. After editing, click **Save Project**. When you're ready, click **Publish** to apply the changes to the generated site files.

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

Whenever you add or edit projects, you can either click **Publish** in the UI or run `python build_portfolio_site.py`.
Commit the updated `docs/data/projects.json` and `docs/project-assets/` output.

