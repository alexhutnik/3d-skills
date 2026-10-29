---
name: inspect-3d
description: Create offline HTML reviews of CAD parts and assemblies, with named parts and exploded views. Use a live browser viewer when the review needs Python calculations or model changes.
---

# Inspect 3D designs in a browser

Resolve this skill folder from the loaded `SKILL.md` path. Follow symbolic links.
Use its absolute path as `SKILL_DIR` in the commands below.
Run `uv sync --project "$SKILL_DIR" --locked --no-dev` before using its scripts.
Run scripts with `uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/scripts/<script>.py"`.
The first run can download Python and dependencies. Keep generated files in the user project.


Prefer a browser surface for this repository.
Use an existing viewer before writing a new viewer.
Python can control the exact geometry while the browser provides the interactive surface.
Browser support does not prove that an app can embed the viewer in every canvas surface.
Test embedding separately before promising it.

Default to a self-contained HTML file for review and sharing.
Use `scripts/export_review.py` to embed the meshes and viewer in that file.
It opens directly without a server, a network connection, or JavaScript build tools.
Keep the file with its model revision. Do not imply that an old review updates after a CAD change.

Read [viewer operation](references/viewers.md) for export, checks, and live viewer commands.
Run these tools through this skill's `uv` project. Keep dependencies in `pyproject.toml` and `uv.lock`.
Use Typer for command-line arguments and Rich for useful status messages.
Add a local Python server when live model changes or exact calculations improve the review.
Use OCP Viewer for Python-controlled assembly views and explicit motion tracks.
Consider cadgen for its selection references and annotation tools.
Keep its environment separate from projects that use a different build123d version.
Do not copy upstream JavaScript animation examples into this Python-only repository.

Both viewer scripts accept a STEP assembly described by a JSON scene.
Read [the scene format](references/scene.md) before creating a scene.
Group each purchased component as one part, even if its STEP file contains many solids.
Use different colors for printed parts and purchased parts.
Show an assembled view first. Explain that an exploded view changes display positions only.
Test the HTML file with network access disabled. Check reopening, part visibility, and separation.
Inspect the rendered result. A successful export command does not prove that the browser shows the model.

For a review, choose views that answer a design question.
Use sections for wall thickness, seats, and internal interference.
Use exact geometry for fit measurements. State when a number comes only from a viewer mesh.
Keep manufacturer files and unsupported cable envelopes visibly distinct.

A motion animation presents positions. It does not validate a mechanism or collision freedom.
Use `../design-assemblies/SKILL.md` for those checks.
Re-select geometry after a rebuild because numeric face identifiers can change.
