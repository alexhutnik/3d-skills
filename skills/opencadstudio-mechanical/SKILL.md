---
name: opencadstudio-mechanical
description: "Build and edit mechanical parts through OpenCADStudio MCP. Save native drawings, create printable exports without save dialogs, and check the resulting geometry. Use for OCS enclosure and part projects."
---

# OpenCADStudio mechanical parts

Resolve this skill folder from the loaded `SKILL.md` path. Follow symbolic links.
Use its absolute path as `SKILL_DIR` in the commands below.
Run `uv sync --project "$SKILL_DIR" --locked --no-dev` before using its scripts.
Run scripts with `uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/scripts/<script>.py"`.
The first run can download Python and dependencies. Keep generated files in the user project.


Use OCS for the requested model. Use Python only for custom code.
Keep the part requirements separate from the available CAD operations.
Do not silently remove required geometry to make an operation pass.

## Select the automation channel

Discover the available OCS MCP tools first.
Call `ocs_sessions`, then read `capabilities` and the relevant command manifests.
Report the version, build, and schema digest at the first connection.
Read `record_schema` before editing unfamiliar database records.

The MCP tools attach to a running editor. They can work without clicks, but the editor needs a display.
For work without an editor window, use the installed executable with `--serve`.
That channel owns a separate drawing session. It does not operate on the user's active drawing.
The bundled Python session helper uses this channel.
The tested executable path is for macOS. Pass `--executable` when its location differs.

## Build and retain useful edits

Create a separate drawing for the project. Set `INSUNITS 4` for millimeters.
Set `SOLIDHIST 1` before Boolean operations when the part needs retained operand history.
Keep a Python recipe and a parameter file for coordinated changes.
Retained history permits individual edits; it does not automatically preserve every relationship between dimensions.

Use native primitives, cuts, unions, and edge operations.
For stepped openings, extend each cutter beyond the face that it must remove.
Keep the flat bonding shelf as a distinct, measurable face.
Save intermediate stages before difficult operations.

Follow the returned command state after every interactive step.
Use `entity` input when the manifest requests an entity pick.
Do not substitute `structure` input. In the tested fillet command, that ended the command without changing geometry.
A `completed` response alone does not prove that the model changed.
Check the revision, entities, and resulting geometry.

Read `properties` for the current selection before editing native dimensions.
Use the advertised property identifiers and available operand choices.
Tested fields include `solid_history_length` and `solid_history_operand`.
Reopen the native drawing and measure the edited result.

For concrete command sequences, read [the workflow](references/workflow.md).
The enclosure example demonstrates a hollow body, stepped openings, and vertical corner rounds.

## Save and export without dialogs

Run `audit` for the intended native format, then use `save_verified` with an absolute path.
Check the returned verification result and the actual file.
This operation can leave the working document marked as changed.
Do not discard it until the saved file has passed its checks.

On OCS 2026.41, `STLOUT` and `STEPOUT` open native save dialogs.
`-STLOUT` is unknown. The command-line `--export` converter does not support STL output.
Do not use those paths for an unattended export on this build.
Do not treat an MCP success response as proof that an export file exists.

The verified route is:

1. Save the OCS drawing and obtain its native ACIS geometry through `query` or `records`.
2. If the payload is binary SAB, save a verified DXF 2000 copy and reopen that copy.
3. Extract its ASCII SAT payload. Keep the original drawing unchanged.
4. Convert that payload with `scripts/convert_acis.py`.
5. Check the exported STL with `scripts/check_mesh.py`.

ACIS is the solid geometry stored inside the drawing. SAT and SAB are its text and binary forms.
This route uses an external Python conversion library. It converts the actual OCS model; it does not rebuild the part.
The OCS export command itself still requires a dialog.

The pinned `cq-acis` library is experimental. It can reject unsupported surfaces or malformed boundaries.
Do not accept a partial body or suppress conversion errors.
If conversion fails, preserve the native drawing and report the exact error.
Use another CAD approach only when the requested scope permits it, and identify that fallback clearly.

## Check units and geometry

Require an explicit working unit and expected dimensions before conversion.
The tested OCS SAT header declares 10 mm per coordinate unit, although the intended model uses 1 mm.
The converter reads that declaration and applies the caller's explicit unit correction.
It records the correction in its report. Never apply a fixed correction to arbitrary imported geometry.
Check dimensions after conversion. Do not infer correctness from the header or preview alone.

Require one valid solid for a single-part enclosure.
Check the exterior dimensions, wall thickness, recess depth, shelf planes, and reference hardware clearance.
Keep the hardware out of the printable export.
Check the STL for a closed surface, consistent face directions, one connected body, and positive volume.
Compare its dimensions and volume with the intended solid.
The bundled checks use 0.05 mm for dimensions and 0.1 percent for volume.
Choose tighter or different limits when the part requires them; record the limits before testing.

OCS measurement bounds can be zero after reopening a drawing.
Its mesh measurements also use a coarse approximation of curved faces.
Use the converted solid and the independent STL check for final dimensions and mesh closure.
Native audit and roundtrip checks do not establish printability.

## Recover from failures

Preserve the document identifier, revision, and operation identifier for every mutation.
After a tool timeout, inspect the existing operation. Do not replay it with a new identifier.
`running` and `waiting_input` are not completion states.
A selection can succeed while the enclosing command still reports `waiting_input`.
Continue with the required command input.

On this build, a perimeter fillet chain that includes curved edges fails with `is not straight`.
Vertical straight corner edges work. Do not repeatedly retry the unsupported perimeter round with different pick coordinates.
The tested perimeter round also fails after drilling because the body contains an unsupported cylindrical face.
Record the omitted round or use an authorized fallback that can preserve the required shape.

For visual checks in an editor session, use `ocs_capture` with `annotate: true` and `diff: true`.
Inline delivery worked in this investigation; resource delivery returned a transport error.
Capture is unavailable in a session without an editor window.

## Deliver the result

Keep the native drawing, parameter recipe, printable file, and validation report in the project directory.
State any external conversion step and any unimplemented geometry.
The supported operations and tested limits are in [the workflow](references/workflow.md).
Do not describe physical fit, adhesive strength, or load capacity as verified by geometry checks.
