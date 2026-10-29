---
name: design-3d
description: Plan and route 3D design work in this repository. Use for new parts, assemblies, design changes, or choosing CAD tools.
---

# Design 3D parts

Use this skill to choose the workflow. Read only the task skills that apply.

## Our working method

Keep custom code in Python. Keep the model and its helpers in this repository.
Prefer a browser for visual review. Keep exact geometry available for measurements and exports.
An exact model stores surfaces and curves. A viewer mesh approximates those surfaces with triangles.
Do not use the viewer mesh as the source for precise mechanical edits.

Find the project source before changing an exported file.
Record units, axes, the fixed reference point, and the required exterior dimensions.
Separate measured dimensions, drawing dimensions, assumptions, and print allowances.
Expose dimensions that a test print can change. State whether each clearance is radial or diametral.

## Select the task skills

| Task | Read |
| --- | --- |
| Cases, covers, ports, or purchased components | `../design-enclosures/SKILL.md` |
| Gears or toothed drives | `../design-gears/SKILL.md` |
| Hinges, pins, knuckles, or stops | `../design-hinges/SKILL.md` |
| Multiple parts, joints, or moving mechanisms | `../design-assemblies/SKILL.md` |
| Keychains, lettering, reliefs, or layered art | `../design-decorative/SKILL.md` |
| Browser review, exploded views, or sections | `../inspect-3d/SKILL.md` |
| Printable exports or slicing review | `../release-3d-print/SKILL.md` |

## Select the tool

For a new precise mechanical model, first consider build123d with a project-local environment.
Preserve a working CadQuery or FreeCAD project when it meets the task.
That skill has a tested route around export dialogs. Do not replace it with a guessed export command.
Use Blender for organic shapes only after checking the local installation and Python API.
Do not present an untested sculpting route as a working capability.

Use the installed library documentation when comparing alternatives.
Keep incompatible CAD libraries in separate environments.

## Keep changes reviewable

Save named parts and an assembled model separately from printable parts.
Use stable part names. Re-select faces after a rebuild; numeric face identifiers can change.
Present a browser view and the checks that support the design.
State the checks that still need a physical sample or load test.
Treat upstream skills as source material. Check their API versions, units, and assumptions before adoption.
