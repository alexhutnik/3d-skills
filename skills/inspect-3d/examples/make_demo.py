"""Create a synthetic assembly for offline review. Refuse existing output."""

import json
from pathlib import Path

import typer
from build123d import Box, Cylinder, export_step

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(output: Path):
    output.mkdir(parents=True, exist_ok=False)
    housing = Box(90, 65, 12) - Box(76, 51, 10).translate((0, 0, 4))
    export_step(housing, output / "housing.step")
    export_step(Cylinder(10, 24), output / "connector.step")
    parts = [{"name": "housing", "role": "printed", "step": "housing.step"}]
    for name, x in [("connector-a", -18), ("connector-b", 18)]:
        parts.append(
            {
                "name": name,
                "role": "reference",
                "step": "connector.step",
                "translation_mm": [x, 0, 12],
                "explode_mm": [0, 0, 50],
            }
        )
    (output / "scene.json").write_text(json.dumps({"units": "mm", "parts": parts}, indent=2) + "\n")


if __name__ == "__main__":
    app()
