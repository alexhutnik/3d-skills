"""Compare an unmodified STL with a STEP and explicit design requirements."""

import typer
from typing import Annotated
from types import SimpleNamespace
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from build123d import import_step


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise typer.BadParameter("Use a finite positive number")
    return number


def check(step, stl, size, bodies, linear_tolerance, volume_tolerance):
    solid = import_step(step)
    solids = list(solid.solids())
    if not solids:
        raise ValueError("The STEP has no solids")
    box = solid.bounding_box()
    bounds = np.array([tuple(box.min), tuple(box.max)], dtype=float)
    volume = float(sum(s.volume for s in solids))
    if not math.isfinite(volume) or volume <= 0:
        raise ValueError("The STEP volume must be finite and positive")
    mesh = trimesh.load_mesh(stl, process=False)
    if not isinstance(mesh, trimesh.Trimesh) or not len(mesh.faces):
        raise ValueError("The STL does not contain a triangle mesh")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("The STL contains nonfinite coordinates")
    face_count = len(mesh.faces)
    # STL repeats vertices per triangle. Merge positions without filling holes,
    # changing winding, or deleting faces.
    mesh.merge_vertices()
    counts = np.bincount(mesh.edges_unique_inverse)
    components = mesh.split(only_watertight=False)
    size_error = float(np.max(np.abs(mesh.extents - size)))
    step_size_error = float(np.max(np.abs(np.ptp(bounds, axis=0) - size)))
    bounds_error = float(np.max(np.abs(mesh.bounds - bounds)))
    volume_error = abs(float(mesh.volume) - volume) / volume if volume > 0 else math.inf
    checks = {
        "native_valid": bool(solid.is_valid and all(s.is_valid for s in solids)),
        "native_positive": bool(all(s.volume > 0 for s in solids)),
        "native_solid_count": len(solids) == bodies,
        "mesh_body_count": len(components) == bodies,
        "mesh_closed": bool(mesh.is_watertight and np.all(counts == 2)),
        "mesh_winding": bool(mesh.is_winding_consistent),
        "mesh_positive_components": bool(all(c.is_volume and c.volume > 0 for c in components)),
        "triangles_preserved": len(mesh.faces) == face_count,
        "required_mesh_size": size_error <= linear_tolerance,
        "required_native_size": step_size_error <= linear_tolerance,
        "matching_placement": bounds_error <= linear_tolerance,
        "matching_volume": volume_error <= volume_tolerance,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "step": str(step),
        "stl": str(stl),
        "sha256": {p.suffix: hashlib.sha256(p.read_bytes()).hexdigest() for p in (step, stl)},
        "required_size_mm": size,
        "required_bodies": bodies,
        "native_solids": len(solids),
        "mesh_bodies": len(components),
        "native_bounds_mm": bounds.tolist(),
        "mesh_bounds_mm": mesh.bounds.tolist(),
        "native_volume_mm3": volume,
        "mesh_volume_mm3": float(mesh.volume),
        "mesh_size_error_mm": size_error,
        "native_size_error_mm": step_size_error,
        "bounds_error_mm": bounds_error,
        "relative_volume_error": volume_error,
        "linear_tolerance_mm": linear_tolerance,
        "relative_volume_tolerance": volume_tolerance,
        "triangles": face_count,
        "limits": "No repair. Vertex merging only. Does not prove local wall thickness, fit, or strength.",
    }


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(
    step: Path,
    stl: Path,
    size: Annotated[tuple[float, float, float], typer.Option()],
    bodies: Annotated[int, typer.Option(min=1)],
    report: Annotated[Path, typer.Option()],
    linear_tolerance: Annotated[float, typer.Option()] = 0.05,
    volume_tolerance: Annotated[float, typer.Option()] = 0.001,
):
    args = SimpleNamespace(**locals())
    if report.resolve() in (step.resolve(), stl.resolve()):
        raise typer.BadParameter("The report must not replace an input file")
    for value in (*args.size, args.linear_tolerance, args.volume_tolerance):
        positive(value)
    try:
        result = check(
            args.step.resolve(),
            args.stl.resolve(),
            args.size,
            args.bodies,
            args.linear_tolerance,
            args.volume_tolerance,
        )
    except (OSError, ValueError, TypeError, RuntimeError, ImportError) as error:
        result = {"passed": False, "error": f"{type(error).__name__}: {error}"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    app()
