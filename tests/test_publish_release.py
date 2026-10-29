import importlib.util
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publish_release", ROOT / "scripts/publish_release.py")
publish_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish_release)


@pytest.fixture
def release_files(tmp_path):
    archive = tmp_path / "3d-skills-v1.0.0.zip"
    checksum = archive.with_suffix(".zip.sha256")
    notes = tmp_path / "CHANGELOG.md"
    archive.write_bytes(b"checked archive")
    checksum.write_text("checked checksum")
    notes.write_text("Release notes")
    return archive, checksum, notes


def invoke(files):
    archive, _, notes = files
    return CliRunner().invoke(
        publish_release.app,
        ["v1.0.0", "example/skills", "--output", str(archive.parent), "--notes", str(notes)],
    )


def test_publication_can_repeat_without_duplicate_release(monkeypatch, release_files):
    archive, checksum, notes = release_files
    releases = {}
    assets = {}
    calls = []

    def gh(command, **kwargs):
        assert kwargs["check"]
        calls.append(command)
        if command[1] == "api":
            assert "--paginate" in command
            return subprocess.CompletedProcess(command, 0, stdout="\n".join(releases))
        operation, tag = command[2:4]
        if operation == "create":
            assert tag not in releases, "GitHub rejects duplicate release creation"
            assert "--verify-tag" in command
            releases[tag] = True
        elif operation == "upload":
            assert tag in releases
            assert "--clobber" in command
        elif operation == "edit":
            assert tag in releases
            assert command[command.index("--notes-file") + 1] == str(notes)
            return subprocess.CompletedProcess(command, 0)
        else:
            pytest.fail(f"Unexpected command: {command}")
        assert command[4:6] == [str(archive), str(checksum)]
        for path in (archive, checksum):
            assets[path.name] = path.read_bytes()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(publish_release.subprocess, "run", gh)
    assert invoke(release_files).exit_code == 0
    assets["unrelated.txt"] = b"Keep this file"
    archive.write_bytes(b"replacement archive")
    checksum.write_text("replacement checksum")
    assert invoke(release_files).exit_code == 0
    assert assets[archive.name] == archive.read_bytes()
    assert assets[checksum.name] == checksum.read_bytes()
    assert assets["unrelated.txt"] == b"Keep this file"
    assert [command[2] for command in calls if command[1] == "release"] == ["create", "upload", "edit"]


def test_failed_query_does_not_publish(monkeypatch, release_files):
    calls = []

    def fail_query(command, **kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command, stderr="The request failed")

    monkeypatch.setattr(publish_release.subprocess, "run", fail_query)
    result = invoke(release_files)
    assert result.exit_code != 0
    assert len(calls) == 1
    assert calls[0][1] == "api"


def test_failed_upload_stops_publication(monkeypatch, release_files):
    calls = []

    def fail_upload(command, **kwargs):
        calls.append(command)
        if command[1] == "api":
            return subprocess.CompletedProcess(command, 0, stdout="v1.0.0\n")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(publish_release.subprocess, "run", fail_upload)
    result = invoke(release_files)
    assert result.exit_code != 0
    assert [command[2] for command in calls if command[1] == "release"] == ["upload"]


@pytest.mark.parametrize("missing", [0, 1, 2])
def test_missing_files_stop_before_remote_access(monkeypatch, release_files, missing):
    release_files[missing].unlink()

    def unexpected(*args, **kwargs):
        pytest.fail("Missing files must stop publication before a GitHub request")

    monkeypatch.setattr(publish_release.subprocess, "run", unexpected)
    result = invoke(release_files)
    assert result.exit_code == 2
    assert "release file is missing" in result.output
