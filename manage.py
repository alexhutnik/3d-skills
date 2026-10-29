"""Install links, prepare isolated environments, test, and package the skills."""

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
PROFILES = {"inspect": "inspect-3d", "print": "release-3d-print", "ocs": "opencadstudio-mechanical"}
app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
console = Console()


def skills(root=ROOT):
    return sorted(path.parent for path in (root / "skills").glob("*/SKILL.md"))


def selected(profile):
    if profile == "all":
        return list(PROFILES.values())
    if profile not in PROFILES:
        raise typer.BadParameter("Choose inspect, print, ocs, or all")
    return [PROFILES[profile]]


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
    return pairs


@app.command()
def link(destination: Annotated[Path, typer.Option(help="Use .agents/skills for Codex or .claude/skills for Claude.")]):
    """Link all nine skills. Refuse existing files and unrelated links."""
    try:
        pairs = install_links(destination)
    except (OSError, ValueError) as error:
        console.print(str(error), markup=False)
        raise typer.Exit(1) from error
    console.print(f"Linked {len(pairs)} skills in {destination}", markup=False)


@app.command()
def unlink(destination: Annotated[Path, typer.Option()]):
    """Remove only links that point to this checkout. Keep all other files."""
    for source in skills():
        target = destination.expanduser() / source.name
        if target.is_symlink() and target.resolve() == source.resolve():
            target.unlink()
            console.print(f"Removed {target}", markup=False)


@app.command()
def setup(profile: str = "all", dev: bool = False, browser: bool = False):
    """Install locked dependencies. uv downloads Python when needed."""
    if browser and profile not in ("all", "inspect"):
        raise typer.BadParameter("The browser requires the inspect profile")
    for name in selected(profile):
        run(["uv", "sync", "--project", str(ROOT / "skills" / name), "--locked", *([] if dev else ["--no-dev"])])
    if browser:
        run(
            [
                "uv",
                "run",
                "--project",
                str(ROOT / "skills/inspect-3d"),
                "--locked",
                "--no-dev",
                "playwright",
                "install",
                "chromium",
            ]
        )


@app.command()
def doctor(profile: str = "all"):
    """Check installed environments without installing dependencies."""
    imports = {
        "inspect-3d": "build123d, k3d, ocp_viewer, playwright",
        "release-3d-print": "build123d, trimesh, scipy, networkx",
        "opencadstudio-mechanical": "cadquery, cq_acis, trimesh",
    }
    failed = False
    for name in selected(profile):
        project = ROOT / "skills" / name
        executable = project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not executable.is_file():
            console.print(f"Missing environment: {name}. Run setup.")
            failed = True
            continue
        environment = os.environ.copy()
        environment.pop("VIRTUAL_ENV", None)
        result = subprocess.run(
            [
                "uv",
                "run",
                "--project",
                str(project),
                "--no-sync",
                "--no-dev",
                "python",
                "-c",
                f"import {imports[name]}; print('Imports passed: {name}')",
            ],
            check=False,
            env=environment,
        )
        failed |= result.returncode != 0
    console.print(f"FFmpeg for video export: {shutil.which('ffmpeg') or 'not installed (optional)'}", markup=False)
    console.print("OpenCADStudio is optional. Native OCS commands require a separate application installation.")
    if failed:
        raise typer.Exit(1)


@app.command()
def test(browser: bool = False):
    """Run pytest in each isolated environment. Add --browser for browser checks."""
    run(["uv", "run", "--locked", "ruff", "check", "."])
    run(["uv", "run", "--locked", "ruff", "format", "--check", "."])
    run(["uv", "run", "--locked", "pytest", "-q"])
    for name in PROFILES.values():
        project = ROOT / "skills" / name
        marker = ["-m", "not browser"] if name == "inspect-3d" and not browser else []
        run(["uv", "run", "--project", str(project), "--locked", "pytest", "-q", *marker], cwd=project)


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
