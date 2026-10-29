"""Show named STEP parts in OCP Viewer. Never write manufacturing geometry."""

import json
import math
from pathlib import Path
from typing import Annotated

import typer
from build123d import Axis, Compound, import_step
from rich.console import Console

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
console = Console()


def vector(value, name):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must contain three numbers")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value):
        raise ValueError(f"{name} must contain finite numbers")
    return value


def load_scene(path):
    data = json.loads(path.read_text())
    if data.get("units") != "mm":
        raise ValueError("The scene must declare units: mm")
    if not isinstance(data.get("parts"), list) or not data["parts"]:
        raise ValueError("The scene must contain parts")
    shapes, parts, names = [], [], set()
    cache = {}
    for item in data["parts"]:
        name = item["name"]
        if not isinstance(name, str) or not name or "/" in name or name in names:
            raise ValueError("Part names must be unique, nonempty, and contain no slash")
        names.add(name)
        if item.get("role") not in ("printed", "reference"):
            raise ValueError(f"Declare the role for {name}")
        source = (path.parent / item["step"]).resolve()
        if source.suffix.lower() not in (".step", ".stp"):
            raise ValueError("Only STEP input is supported")
        if source not in cache:
            cache[source] = import_step(source)
        imported = cache[source]
        # Flatten topology into one rigid display object. Keep every component
        # placement from the imported assembly. Do not edit the source shape.
        shape = Compound(list(imported.solids()))
        if not shape.is_valid or not shape.solids():
            raise ValueError(f"Invalid or empty input: {source}")
        for axis, angle in zip((Axis.X, Axis.Y, Axis.Z), vector(item.get("rotation_deg", [0, 0, 0]), "rotation_deg")):
            if angle:
                shape = shape.rotate(axis, angle)
        shape = shape.translate(vector(item.get("translation_mm", [0, 0, 0]), "translation_mm"))
        vector(item.get("explode_mm", [0, 0, 0]), "explode_mm")
        shape.label = name
        shapes.append(shape)
        parts.append(item)
    return shapes, parts


@app.command()
def main(
    scene: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    port: Annotated[int, typer.Option(min=1, max=65535)] = 3939,
    motion: Annotated[bool, typer.Option(help="Add a timeline for part separation.")] = False,
    check_only: Annotated[bool, typer.Option(help="Validate without a viewer.")] = False,
):
    """Show a STEP assembly in the running OCP Viewer."""
    shapes, parts = load_scene(scene.resolve())
    if check_only:
        print(
            json.dumps(
                {
                    "parts": [
                        {"name": p["name"], "role": p["role"], "solids": len(s.solids())} for s, p in zip(shapes, parts)
                    ]
                }
            )
        )
        return
    from ocp_viewer import Animation, Camera, Collapse, show

    show(
        *shapes,
        names=[p["name"] for p in parts],
        colors=[p.get("color", "#6f8192" if p["role"] == "printed" else "#d7a95b") for p in parts],
        port=port,
        collapse=Collapse.ROOT,
        reset_camera=Camera.RESET,
        zoom=0.65 if motion else 1.0,
        progress=None,
    )
    if motion:
        animation = Animation()
        for p in parts:
            offset = p.get("explode_mm", [0, 0, 0])
            if any(offset):
                matches = [path for path in animation.paths if path.rsplit("/", 1)[-1] == p["name"]]
                if len(matches) != 1:
                    raise ValueError(f"Cannot identify the rigid display group: {p['name']}")
                animation.add_track(matches[0], "t", [0, 2], [[0, 0, 0], offset])
        if not animation.tracks:
            raise ValueError("The scene has no nonzero explode_mm offsets")
        animation.animate(1)
    console.print(f"Viewer: http://127.0.0.1:{port}/viewer", markup=False)
    console.print("Inspection motion changes the display only. It does not check collisions.")


if __name__ == "__main__":
    app()
