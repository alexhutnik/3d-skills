import hashlib
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import manage


def test_install_repeat_and_remove(tmp_path):
    destination = tmp_path / "project with spaces/.agents/skills"
    manage.install_links(destination)
    manage.install_links(destination)
    assert len(list(destination.iterdir())) == 8
    for source in manage.skills():
        assert (destination / source.name / "SKILL.md").read_bytes() == (source / "SKILL.md").read_bytes()
        assert (destination / source.name).resolve().parents[1] == ROOT
    keep = destination / "unrelated"
    keep.mkdir()
    result = CliRunner().invoke(manage.app, ["unlink", "--destination", str(destination)])
    assert result.exit_code == 0, result.output
    assert list(destination.iterdir()) == [keep]


@pytest.mark.parametrize("kind", ["directory", "file", "broken-link", "other-link"])
def test_conflict_changes_nothing(tmp_path, kind):
    destination = tmp_path / "skills"
    destination.mkdir()
    target = destination / "release-3d-print"
    if kind == "directory":
        target.mkdir()
    elif kind == "file":
        target.write_text("Keep this file")
    else:
        other = tmp_path / "other"
        if kind == "other-link":
            other.mkdir()
        target.symlink_to(other)
    with pytest.raises(ValueError, match="already contains"):
        manage.install_links(destination)
    assert list(destination.iterdir()) == [target]


def test_install_rolls_back_on_failure(tmp_path, monkeypatch):
    original = Path.symlink_to
    count = 0

    def fail_second(path, *args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("No link permission")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "symlink_to", fail_second)
    with pytest.raises(OSError):
        manage.install_links(tmp_path / "skills")
    assert not list((tmp_path / "skills").iterdir())


@pytest.mark.parametrize("operation", ["link", "unlink"])
def test_removed_skill_links_do_not_survive_update(tmp_path, monkeypatch, operation):
    root = tmp_path / "repository"
    source = root / "skills/current"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("Current skill")
    destination = tmp_path / "installed"
    destination.mkdir()
    removed = destination / "removed"
    removed.symlink_to(root / "skills/removed", target_is_directory=True)
    unrelated = destination / "unrelated"
    unrelated.symlink_to(tmp_path / "another-repository/skills/removed", target_is_directory=True)
    if operation == "link":
        manage.install_links(destination, root)
        assert (destination / "current/SKILL.md").is_file()
    else:
        original = manage.owned_links
        monkeypatch.setattr(manage, "owned_links", lambda path: original(path, root))
        result = CliRunner().invoke(manage.app, ["unlink", "--destination", str(destination)])
        assert result.exit_code == 0, result.output
    assert not removed.is_symlink()
    assert unrelated.is_symlink()


def test_versions_and_marketplace_paths():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    for path in [ROOT / "plugin.json", ROOT / ".codex-plugin/plugin.json", ROOT / ".claude-plugin/plugin.json"]:
        data = json.loads(path.read_text())
        assert data["version"] == version
        assert data["name"] == "3d-skills"
    assert (ROOT / "uv.lock").is_file()
    assert not list((ROOT / "skills").glob("*/pyproject.toml"))
    assert not list((ROOT / "skills").glob("*/uv.lock"))
    for path in [ROOT / ".agents/plugins/marketplace.json", ROOT / ".claude-plugin/marketplace.json"]:
        entry = json.loads(path.read_text())["plugins"][0]
        source = entry["source"]
        target = source["path"] if isinstance(source, dict) else source
        assert (ROOT / target / "skills").is_dir()


def test_skill_references_stay_in_package():
    for skill in manage.skills():
        text = (skill / "SKILL.md").read_text()
        metadata = yaml.safe_load(text.split("---", 2)[1])
        assert metadata["name"] == skill.name
        assert isinstance(metadata["description"], str) and metadata["description"]
        for path in skill.rglob("*.md"):
            if ".venv" in path.parts:
                continue
            text = path.read_text()
            assert "/Users/" not in text
            assert "couch_usb_console" not in text
            for match in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
                if "://" in match:
                    continue
                target = (path.parent / match).resolve()
                assert target.is_relative_to(ROOT), (path, match)
                assert target.exists(), (path, match)
            for match in re.findall(r"`(\.\./[^`]+\.md)`", text):
                assert (path.parent / match).resolve().is_file(), (path, match)


def test_complete_reproducible_archive(tmp_path):
    first = manage.build_archive(tmp_path / "first")
    second = manage.build_archive(tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert "plugin.json" in names
        assert "manage.py" in names
        assert "uv.lock" in names
        assert "pyproject.toml" in names
        assert [name for name in names if name.endswith("uv.lock")] == ["uv.lock"]
        assert [name for name in names if name.endswith("pyproject.toml")] == ["pyproject.toml"]
        assert sum(name.endswith("/SKILL.md") for name in names) == 8
        assert not any(".venv/" in name or "__pycache__/" in name or name.startswith("/") for name in names)
        archive.extractall(tmp_path / "unpacked")
    manage.install_links(tmp_path / "installed", tmp_path / "unpacked")
    assert (tmp_path / "installed/inspect-3d/scripts/export_review.py").is_file()
    assert (tmp_path / "installed/inspect-3d").resolve().parents[1] == tmp_path / "unpacked"
    checksum = hashlib.sha256(first.read_bytes()).hexdigest()
    assert first.with_suffix(".zip.sha256").read_text().startswith(checksum)


def test_release_tag_matches_version():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert CliRunner().invoke(manage.app, ["verify-tag", f"v{version}"]).exit_code == 0
    assert CliRunner().invoke(manage.app, ["verify-tag", "v0.0.0"]).exit_code == 2


def test_archive_rejects_path_escape(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    from test_archive import app

    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "Do not write this")
    result = CliRunner().invoke(app, [str(archive)])
    assert result.exit_code != 0
    assert "unsafe path" in str(result.exception)


@pytest.mark.parametrize("dev", [False, True])
@pytest.mark.parametrize("browser", [False, True])
def test_setup_uses_shared_project(monkeypatch, dev, browser):
    calls = []
    monkeypatch.setattr(manage, "run", lambda command: calls.append(command))
    options = (["--dev"] if dev else []) + (["--browser"] if browser else [])
    result = CliRunner().invoke(manage.app, ["setup", *options])
    assert result.exit_code == 0, result.output
    assert calls[0] == ["uv", "sync", "--project", str(ROOT), "--locked", *([] if dev else ["--no-dev"])]
    if browser:
        assert calls[1] == [
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
    assert len(calls) == 1 + browser


def test_setup_rejects_removed_profiles(monkeypatch):
    calls = []
    monkeypatch.setattr(manage, "run", lambda *args, **kwargs: calls.append(args))
    result = CliRunner().invoke(manage.app, ["setup", "--profile", "print", "--browser"])
    assert result.exit_code == 2
    assert not calls
