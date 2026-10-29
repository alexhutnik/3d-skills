"""Convert native SAT geometry to STEP and STL without an editor. Use uv run."""

import typer
from typing import Annotated
from types import SimpleNamespace
import hashlib
import math
import importlib.metadata
import json
from pathlib import Path

import cadquery as cq
from cq_acis import convert_model, parse_sat_model, parse_sab_model


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(
    source: Path,
    output: Path,
    source_unit_mm: Annotated[float, typer.Option()],
    size: Annotated[tuple[float, float, float], typer.Option()],
    volume: Annotated[float, typer.Option()],
):
    args = SimpleNamespace(**locals())
    if not all(math.isfinite(v) and v > 0 for v in (*size, volume, source_unit_mm)):
        raise typer.BadParameter("Dimensions, units, and volume must be finite and positive")
    if args.output.exists():
        raise typer.BadParameter("Output directory already exists. Use a new path.")
    if args.source_unit_mm <= 0 or args.volume <= 0:
        raise typer.BadParameter("Units and expected volume must be positive.")
    data = args.source.read_bytes()
    binary = data.startswith(b"ACIS BinaryFile") or data.startswith(b"ASM BinaryFile")
    model = parse_sab_model(data, source_id=str(args.source)) if binary else parse_sat_model(data)
    declared_units = model.metadata.units_mm
    if declared_units is None or declared_units <= 0:
        raise ValueError("SAT has no positive unit scale")
    shapes = convert_model(model)
    if len(shapes) != 1:
        raise ValueError(f"Expected one body, got {len(shapes)}")
    scale = args.source_unit_mm / declared_units
    shape = shapes[0].scale(scale) if scale != 1 else shapes[0]
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Conversion did not produce one valid solid")
    bounds = shape.BoundingBox()
    size = [bounds.xlen, bounds.ylen, bounds.zlen]
    size_error = max(abs(a - b) for a, b in zip(size, args.size))
    volume = shape.Volume()
    volume_error = abs(volume - args.volume) / args.volume
    report = {
        "source": str(args.source.resolve()),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "route": "OCS native ACIS -> cq-acis/OpenCascade -> STEP and STL; no CAD rebuild",
        "source_format": "SAB" if binary else "SAT",
        "declared_source_units_mm": declared_units,
        "explicit_working_unit_mm": args.source_unit_mm,
        "scale_after_conversion": scale,
        "size_mm": size,
        "bounds_mm": [[bounds.xmin, bounds.ymin, bounds.zmin], [bounds.xmax, bounds.ymax, bounds.zmax]],
        "volume_mm3": volume,
        "max_size_error_mm": size_error,
        "relative_volume_error": volume_error,
        "size_tolerance_mm": 0.05,
        "relative_volume_tolerance": 0.001,
        "valid_solid": True,
        "solid_count": len(shape.Solids()),
        "face_count": len(shape.Faces()),
        "stl_linear_tolerance_mm": 0.02,
        "stl_angular_tolerance_rad": 0.1,
        "cq_acis_version": importlib.metadata.version("cq-acis"),
        "cadquery_version": importlib.metadata.version("cadquery"),
    }
    if size_error > 0.05 or volume <= 0 or volume_error > 0.001:
        raise ValueError(f"Dimensions or volume do not match: {report}")
    args.output.mkdir(parents=True, exist_ok=False)
    cq.exporters.export(shape, str(args.output / "part.step"), "STEP")
    cq.exporters.export(shape, str(args.output / "part.stl"), "STL", tolerance=0.02, angularTolerance=0.1)
    reopened = cq.importers.importStep(str(args.output / "part.step")).val()
    if not reopened.isValid() or len(reopened.Solids()) != 1 or abs(reopened.Volume() - volume) / volume > 1e-7:
        raise ValueError("STEP roundtrip failed")
    report["step_roundtrip_passed"] = True
    report["files"] = {
        path.name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in args.output.iterdir()
    }
    (args.output / "conversion.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    app()
