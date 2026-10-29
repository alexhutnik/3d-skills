"""Test an extracted package in a new directory with a fresh shared environment."""

import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

import typer

app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(archive: Path):
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="3d-skills-release-") as directory:
        root = Path(directory).resolve()
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if not (root / name).resolve().is_relative_to(root):
                    raise ValueError("The archive contains an unsafe path")
            bundle.extractall(root)
        subprocess.run(["uv", "run", "--locked", "python", "manage.py", "test"], cwd=root, env=environment, check=True)


if __name__ == "__main__":
    app()
