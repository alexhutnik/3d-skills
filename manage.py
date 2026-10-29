"""Install links, prepare the shared environment, test, and package the skills."""

import hashlib
import os
import shutil
import subprocess
import tomllib
import zipfile
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

ROOT = Path(__file__).resolve().parent
app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
console = Console()


def skills(root=ROOT):
    return sorted(path.parent for path in (root / "skills").glob("*/SKILL.md"))


def run(command, cwd=ROOT):
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    result = subprocess.run(command, cwd=cwd, check=False, env=environment)
    if result.returncode:
        raise typer.Exit(result.returncode)


def install_links(destination, root=ROOT):
    destination = destination.expanduser().absolute()
    pairs = [(source, destination / source.name) for source in skills(root)]
    # Check the complete set before changing any path. Never replace user files.
    for source, target in pairs:
        if os.path.lexists(target) and not (target.is_symlink() and target.resolve() == source.resolve()):
            raise ValueError(f"The destination already contains another skill: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for source, target in pairs:
            if not target.is_symlink():
                target.symlink_to(source.resolve(), target_is_directory=True)
                created.append(target)
    except OSError:
        for target in reversed(created):
            target.unlink()
        raise
    for target in owned_links(destination, root):
        if not (target / "SKILL.md").is_file():
            target.unlink()
    return pairs


def owned_links(destination, root=ROOT):
    if not destination.is_dir():
        return []
    source_folder = (root / "skills").resolve()
    return [
        target for target in destination.iterdir() if target.is_symlink() and target.resolve().parent == source_folder
    ]


@app.command()
def link(destination: Annotated[Path, typer.Option(help="Use .agents/skills for Codex or .claude/skills for Claude.")]):
    """Link all eight skills. Refuse existing files and unrelated links."""
    try:
        pairs = install_links(destination)
    except (OSError, ValueError) as error:
        console.print(str(error), markup=False)
        raise typer.Exit(1) from error
    console.print(f"Linked {len(pairs)} skills in {destination}", markup=False)


@app.command()
def unlink(destination: Annotated[Path, typer.Option()]):
    """Remove only links that point to this checkout. Keep all other files."""
    for target in owned_links(destination.expanduser()):
        target.unlink()
        console.print(f"Removed {target}", markup=False)


@app.command()
def setup(dev: bool = False, browser: bool = False):
    """Install locked dependencies. uv downloads Python when needed."""
    run(["uv", "sync", "--project", str(ROOT), "--locked", *([] if dev else ["--no-dev"])])
    if browser:
        run(
            [
                "uv",
                "run",
                "--project",
                str(ROOT),
                "--locked",
                "--no-dev",
                "playwright",
                "install",
                "chromium",
            ]
        )


@app.command()
def doctor():
    """Check the shared environment without installing dependencies."""
    executable = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        console.print("The shared environment is missing. Run setup.")
        raise typer.Exit(1)
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        [
            str(executable),
            "-c",
            "import build123d, k3d, ocp_viewer, playwright, trimesh, scipy, networkx; "
            "print('Imports passed: shared environment')",
        ],
        check=False,
        cwd=ROOT,
        env=environment,
    )
    console.print(f"FFmpeg for video export: {shutil.which('ffmpeg') or 'not installed (optional)'}", markup=False)
    if result.returncode:
        raise typer.Exit(1)


@app.command()
def test(browser: bool = False):
    """Run all checks in the shared environment. Add --browser for browser checks."""
    run(["uv", "run", "--locked", "ruff", "check", "."])
    run(["uv", "run", "--locked", "ruff", "format", "--check", "."])
    marker = [] if browser else ["-m", "not browser"]
    run(["uv", "run", "--locked", "pytest", "-q", *marker])


def package_files(root):
    files = [
        root / name
        for name in (
            "README.md",
            "LICENSE",
            "NOTICE.md",
            "CHANGELOG.md",
            "AGENTS.md",
            "manage.py",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            ".gitignore",
            "plugin.json",
        )
    ]
    for folder in (
        "skills",
        "docs",
        "tests",
        "scripts",
        ".codex-plugin",
        ".claude-plugin",
        ".agents/plugins",
        ".github",
    ):
        for path in (root / folder).rglob("*"):
            if any(
                part in {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "artifacts"}
                for part in path.relative_to(root).parts
            ):
                continue
            if path.is_symlink():
                raise ValueError(f"The release contains a symbolic link: {path}")
            if path.is_file() and path.suffix not in (".pyc", ".pyo"):
                files.append(path)
    return sorted(set(files))


def build_archive(output, root=ROOT):
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"3d-skills-v{version}.zip"
    # Fixed member dates and order make the same source produce the same archive.
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in package_files(root):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n")
    return archive


@app.command()
def package(output: Path = ROOT / "dist"):
    """Build a complete source and plugin ZIP with a SHA-256 checksum."""
    console.print(str(build_archive(output)), markup=False)


@app.command()
def verify_tag(tag: str):
    """Refuse a release tag that differs from the package version."""
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    if tag != f"v{version}":
        raise typer.BadParameter(f"The release tag must be v{version}")
    console.print(f"Verified {tag}")


if __name__ == "__main__":
    app()
