import json
import sys
from pathlib import Path

import pytest
from build123d import Box, export_step
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from show_scene import app, load_scene
from export_review import app as export_app
from render_video import app as video_app


@pytest.fixture
def scene(tmp_path):
    export_step(Box(10, 20, 30), tmp_path / "part.step")
    path = tmp_path / "scene.json"
    path.write_text(json.dumps({"units": "mm", "parts": [{"name": "part", "role": "printed", "step": "part.step"}]}))
    return path


@pytest.mark.parametrize("defect", ["units", "empty", "duplicate", "role", "nan", "format"])
def test_scene_rejects_invalid_input(scene, defect):
    data = json.loads(scene.read_text())
    if defect == "units":
        data["units"] = "inches"
    elif defect == "empty":
        data["parts"] = []
    elif defect == "duplicate":
        data["parts"].append(data["parts"][0].copy())
    elif defect == "role":
        data["parts"][0]["role"] = "unknown"
    elif defect == "nan":
        data["parts"][0]["translation_mm"] = [float("nan"), 0, 0]
    elif defect == "format":
        data["parts"][0]["step"] = "part.stl"
    scene.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_scene(scene)


def test_check_only_needs_no_server(scene):
    result = CliRunner().invoke(app, [str(scene), "--check-only"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["parts"][0]["solids"] == 1


def test_export_preserves_scene_when_sidecar_name_matches(scene):
    target = scene.with_name("part.review.json")
    scene.rename(target)
    before = target.read_bytes()
    result = CliRunner().invoke(export_app, [str(target), str(target.with_name("part.html"))])
    assert result.exit_code == 2
    assert target.read_bytes() == before


def test_video_reports_missing_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr("render_video.shutil.which", lambda _: None)
    source = tmp_path / "review.html"
    source.write_text("<html></html>")
    result = CliRunner().invoke(video_app, [str(source), str(tmp_path / "output.mp4")])
    assert result.exit_code == 2
    assert "FFmpeg" in result.output
    assert not (tmp_path / "output.mp4").exists()


def test_video_failure_preserves_existing_output(tmp_path, monkeypatch):
    monkeypatch.setattr("render_video.shutil.which", lambda _: "/example/ffmpeg")

    def unavailable_browser():
        raise RuntimeError("The browser failed to start")

    monkeypatch.setattr("render_video.sync_playwright", unavailable_browser)
    source, output = tmp_path / "review.html", tmp_path / "review.mp4"
    source.write_text("<html></html>")
    output.write_bytes(b"Previous video")
    result = CliRunner().invoke(video_app, [str(source), str(output)])
    assert result.exit_code != 0
    assert output.read_bytes() == b"Previous video"
    assert not list(tmp_path.glob("review-video-*"))
