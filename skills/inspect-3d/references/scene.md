# Scene format

The scene describes inspection only. It does not export manufacturing files.
All geometry uses millimeters. All paths are relative to the scene file.
Each input STEP becomes one rigid display part, including its internal solids.

```json
{
  "units": "mm",
  "parts": [
    {
      "name": "housing",
      "role": "printed",
      "step": "../output/housing.step",
      "color": "#566879",
      "rotation_deg": [0, 0, 0],
      "translation_mm": [0, 0, 0],
      "explode_mm": [0, 0, 0]
    },
    {
      "name": "connector",
      "role": "reference",
      "step": "../reference/connector.step",
      "rotation_deg": [-90, 0, 0],
      "translation_mm": [0, 0, 43.65],
      "explode_mm": [0, 0, 65]
    }
  ]
}
```

`name`, `role`, and `step` are required. Names must be unique and contain no slash.
The role is `printed` or `reference`. It controls the default color, not export permission.
Optional vectors default to zero.
Rotations apply around world X, then Y, then Z, in degrees about the origin.
Translation applies after rotation.
`explode_mm` adds a display offset from the assembled position.
The HTML viewer uses time `0` to `1`. OCP Viewer uses a two-second timeline.
It is not a general joint solver or a collision check.
Use separate assemblies or a tested viewer joint API for functional motion.

Run `--check-only` to read the geometry without contacting a viewer.
Do not use imported files with unknown units. Check a known physical dimension first.
