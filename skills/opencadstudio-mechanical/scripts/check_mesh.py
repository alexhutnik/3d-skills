"""Check an STL independently. Do not repair the input. Run with uv run."""

import typer
from typing import Annotated
from types import SimpleNamespace
import hashlib
import math
import json
from pathlib import Path

import numpy as np
import trimesh


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(
    mesh: Path,
    size: Annotated[tuple[float, float, float], typer.Option()],
    volume: Annotated[float, typer.Option()],
    report: Annotated[Path, typer.Option()],
):
    args = SimpleNamespace(**locals())
    if report.resolve() == mesh.resolve():
        raise typer.BadParameter("The report must not replace the input file")
    if not all(math.isfinite(v) and v > 0 for v in (*size, volume)):
        raise typer.BadParameter("Dimensions, units, and volume must be finite and positive")
    mesh = trimesh.load_mesh(args.mesh, process=False)
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("Expected one triangle mesh")
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Input mesh contains nonfinite coordinates")
    original_faces = len(mesh.faces)
    mesh.process(validate=False)
    if len(mesh.faces) != original_faces:
        raise ValueError("Import processing changed the triangle count")
    edge_counts = np.bincount(mesh.edges_unique_inverse)
    size_error = float(np.max(np.abs(mesh.extents - args.size)))
    volume_error = abs(float(mesh.volume) - args.volume) / args.volume
    report = {
        "path": str(args.mesh),
        "sha256": hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
        "triangles": len(mesh.faces),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "bodies": int(mesh.body_count),
        "boundary_edges": int(np.count_nonzero(edge_counts == 1)),
        "nonmanifold_edges": int(np.count_nonzero(edge_counts > 2)),
        "finite": bool(np.isfinite(mesh.vertices).all()),
        "bounds_mm": mesh.bounds.tolist(),
        "size_mm": mesh.extents.tolist(),
        "volume_mm3": float(mesh.volume),
        "max_size_error_mm": size_error,
        "relative_volume_error": volume_error,
        "size_tolerance_mm": 0.05,
        "relative_volume_tolerance": 0.001,
        "repair": "none; standard vertex merging on import only",
        "trimesh_version": trimesh.__version__,
    }
    report["passed"] = bool(
        report["watertight"]
        and report["winding_consistent"]
        and report["bodies"] == 1
        and report["finite"]
        and mesh.volume > 0
        and size_error <= 0.05
        and volume_error <= 0.001
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    app()
