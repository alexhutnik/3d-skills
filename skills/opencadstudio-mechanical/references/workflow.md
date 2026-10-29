# Tested OCS workflow

This workflow targets OCS 2026.41, build `cff240ef71b4`.
Discover the current capabilities when another build is installed.
Run all custom code through Python. Use `uv run` in this repository.

## MCP requests

Read the current state before mutations. Add the current document identifier and revision to each request.
Use a unique request identifier for each new mutation.

Create a document, then run these commands:

```json
{"op":"new","request_id":"example-new"}
{"op":"run","cmd":"INSUNITS 4","request_id":"example-mm"}
{"op":"run","cmd":"SOLIDHIST 1","request_id":"example-history"}
{"op":"run","cmd":"BOX 0,0,0 40,35,0 12","request_id":"example-box"}
```

Query the entities to obtain the created handle.
Create a cutter with `CYLINDER 20,17.5,-1 6 14`.
For subtraction:

1. Select the base handle with `select`.
2. Start `SUBTRACT` with `start`.
3. Select the cutter handles with `select`.
4. Feed `input` with `kind: selection`.
5. Feed `input` with `kind: enter`.
6. Verify the remaining solid and removed cutter handles.

For a union, select the operand handles and run `UNION`.
Query the result instead of assuming that every input handle remains valid.

For vertical corner rounds:

1. Select the solid and start `FILLETEDGE`.
2. Feed token `R`, then the radius as text.
3. Feed each edge with `kind: entity`, its handle, and a point on the edge.
4. Feed Enter for the preview, then Enter to accept it.
5. Verify that the revision and solid changed.

The example script contains these sequences with actual state checks.
Do not copy handles between drawings or sessions.

## Native saving

Use an explicit absolute path:

```json
{"op":"save_verified","path":"/absolute/project/part.dwg","target_format":"dwg","overwrite":false,"request_id":"example-save"}
```

The response must report `verified: true`. Check the file's size and hash.
Use a new path for normal runs. Existing-file conflicts must not trigger a save dialog.
On disposable copies, an explicit `overwrite: true` permits replacement.
Inspect the current file before deliberately replacing it.

## File extraction and conversion

Set `SKILL_DIR` to the absolute path of this installed skill. Follow symbolic links.
Replace input paths, dimensions, and expected volume with values for the actual part.

```sh
uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/scripts/snapshot_native.py" /absolute/project/part.dwg /absolute/project/snapshot
uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/scripts/convert_acis.py" /absolute/project/snapshot/part.sat /absolute/project/converted --source-unit-mm 1 --size 40 35 12 --volume 15018.716965414587
uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/scripts/check_mesh.py" /absolute/project/converted/part.stl --size 40 35 12 --volume 15018.716965414587 --report /absolute/project/converted/mesh-check.json
```

Each output directory must be new. This prevents accidental reuse of an old file.
The snapshot helper starts a private OCS session with `--serve`.
It can read saved drawings without opening an editor window.
For binary payloads, it saves and verifies a DXF 2000 copy, then extracts SAT from that copy.
The tested binary SAB payload used save version 700. The pinned converter rejected it directly.
Do not rename SAB bytes to SAT or assume an older DWG target makes them ASCII.

The conversion helper requires expected dimensions and volume.
For a simple stepped recess, calculate the volume from the box and cylinder dimensions.
For complex parts, use another independent geometric estimate and explicit feature checks.
The OCS coarse mesh volume alone is not an exact reference for curved surfaces.

The helper checks one valid solid and reopens its STEP output.
It writes `part.step`, `part.stl`, and `conversion.json`.
The separate mesh checker writes its own report and returns a failure for invalid geometry.
Neither helper repairs mesh holes or silently changes dimensions.

The STEP and STL retain the model's coordinates.
The enclosure example extends below Z=0. A slicer can place it on the build plate.
If a delivery requires Z=0 at the base, translate the model explicitly and validate the new bounds.

## Editable enclosure example

`examples/build_enclosure.py` accepts a JSON parameter file.
Use `examples/parameters.json` for the complete example schema.
Its dimensions are synthetic. Measure actual hardware before adapting the example.
It creates a rounded faceplate, hollow rear body, and one or two stepped connector openings.
It retains native solid history and saves a parameter copy with the drawing.
It records unsupported cosmetic rounds in `limits.json`.
Do not use it for arbitrary parts that need a different construction.

```sh
uv run --project "$SKILL_DIR" --locked --no-dev python "$SKILL_DIR/examples/build_enclosure.py" /absolute/project/build --parameters /absolute/project/parameters.json
```

Use `properties` on the selected result to discover editable history operands.
Select an advertised `solid_history_operand`, then edit its advertised dimension property.
Tested behavior includes changing a box length after cutting a hole, then saving and reopening that result.
Native operand edits do not automatically update every other operand.
Use the JSON recipe for coordinated changes, then repeat geometry checks.

## Evidence and limits

The original investigation used OCS 2026.41. This package includes automated conversion and protocol tests.
Those tests do not prove that every newer application build behaves the same way.
These tests cover planes, circular holes, cylindrical recesses, straight corner rounds, and simple Boolean operations.
They do not establish support for arbitrary spline surfaces, every ACIS producer, or every OCS feature.
The stalled-operation procedure follows the MCP protocol. This investigation did not force a long-running operation to time out.

Sources: [OCS release source](https://github.com/HakanSeven12/OpenCADStudio/tree/v2026.41),
[cq-acis usage](https://github.com/monozukuri-ai/cq-acis/blob/main/docs/usage.md).
