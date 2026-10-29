---
name: release-3d-print
description: Validate exact solids and exported meshes, prepare printable part files, and review orientation and support choices before printing.
---

# Release parts for printing

Resolve this skill folder from the loaded `SKILL.md` path. Follow symbolic links.
Use its absolute path as `SKILL_DIR` in the commands below.
Set `PLUGIN_DIR` to the directory two levels above the resolved skill folder.
This directory contains the shared `pyproject.toml` and `uv.lock`.
Keep the complete plugin installed. Individual skill folders do not contain a Python project.

```sh
PLUGIN_DIR="$(cd "$SKILL_DIR/../.." && pwd -P)"
```
Run `uv sync --project "$PLUGIN_DIR" --locked --no-dev` before using its scripts.
Run scripts with `uv run --project "$PLUGIN_DIR" --locked --no-dev python "$SKILL_DIR/scripts/<script>.py"`.
The first run can download Python and dependencies. Keep generated files in the user project.


Export only the intended printed parts. Keep purchased components and inspection offsets out of those files.
Keep editable source and an exact STEP export when the project uses solid geometry.
A STEP file is an exchange file. It does not preserve the original feature history.

Check the exact solid before export: validity, positive volume, solid count, dimensions, and required interfaces.
Reopen the export and compare it with the intended geometry.
For an STL and its matching STEP, run `scripts/check_export.py`.
Example after setting `SKILL_DIR` and `PLUGIN_DIR`:

```text
uv run --project "$PLUGIN_DIR" --locked --no-dev python "$SKILL_DIR/scripts/check_export.py" project/output/part.step project/output/part.stl --size 90 65 46 --bodies 1 --report project/output/export-check.json
```

Use the actual required dimensions in this command.
It checks topology, placement, bounds, and volume. It does not check every design requirement.
Give the required size and body count explicitly. Do not derive every expected value from the same faulty export.

Use project checks for mating surfaces, clearances, minimum walls, and assembly paths.
For curved surfaces, choose the mesh tolerance from the required fit accuracy.
A watertight mesh alone does not prove the correct shape.

Choose the print orientation from mating surfaces, visible surfaces, strength, and removable supports.
Inspect the actual layer preview. Check the underside of recess shelves as well as the exterior shoulder.
A flat front face can still contain recessed surfaces that need bridging or supports.
For mixed support materials, inspect the interface assignment, separation settings, and nozzle mapping.
Do not infer the number of nozzle changes from the tower height.
Do not copy a material profile from a previous project without checking the current material.

Report the tested files, limits, print orientation, and physical checks that remain.
Sending a print or changing a printer setting is a separate action from preparing local files.
