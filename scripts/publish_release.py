"""Create a checked release or update its files when a release already exists."""

import subprocess
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(tag: str, repository: str, output: Path = ROOT / "dist", notes: Path = ROOT / "CHANGELOG.md"):
    archive = output / f"3d-skills-{tag}.zip"
    checksum = archive.with_suffix(".zip.sha256")
    for path in (archive, checksum, notes):
        if not path.is_file():
            raise typer.BadParameter(f"The release file is missing: {path}")

    # A failed query must stop publication, not be treated as an absent release.
    result = subprocess.run(
        ["gh", "api", "--paginate", "--jq", ".[].tag_name", f"repos/{repository}/releases"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    common = ["--repo", repository]
    metadata = ["--title", tag, "--notes-file", str(notes)]
    if tag in result.stdout.splitlines():
        subprocess.run(["gh", "release", "upload", tag, str(archive), str(checksum), *common, "--clobber"], check=True)
        subprocess.run(["gh", "release", "edit", tag, *common, *metadata, "--verify-tag"], check=True)
    else:
        subprocess.run(
            ["gh", "release", "create", tag, str(archive), str(checksum), *common, *metadata, "--verify-tag"],
            check=True,
        )


if __name__ == "__main__":
    app()
