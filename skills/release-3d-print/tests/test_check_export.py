import hashlib
import json
import sys
from pathlib import Path

import pytest
import trimesh
from build123d import Box, export_step, export_stl
from typer.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_export import app


@pytest.fixture
def files(tmp_path):
    part = Box(12, 18, 24)
    step, stl = tmp_path / "part.step", tmp_path / "part.stl"
    export_step(part, step)
    export_stl(part, stl)
    return step, stl, tmp_path / "check.json"


def invoke(files, size=(12, 18, 24), bodies=1):
    step, stl, report = files
    return CliRunner().invoke(
        app, [str(step), str(stl), "--size", *map(str, size), "--bodies", str(bodies), "--report", str(report)]
    )


def test_valid_exports_and_source_preservation(files):
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files[:2]]
    result = invoke(files)
    assert result.exit_code == 0, result.output
    report = json.loads(files[2].read_text())
    assert report["passed"]
    assert report["native_volume_mm3"] == pytest.approx(5184)
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in files[:2]]


@pytest.mark.parametrize("defect", ["open", "translated", "two-bodies", "reversed", "corrupt"])
def test_rejects_bad_mesh(files, defect):
    mesh = trimesh.load_mesh(files[1])
    if defect == "open":
        mesh.update_faces(range(len(mesh.faces) - 1))
    elif defect == "translated":
        mesh.apply_translation([3, 0, 0])
    elif defect == "two-bodies":
        other = mesh.copy()
        other.apply_translation([40, 0, 0])
        mesh = trimesh.util.concatenate([mesh, other])
    elif defect == "reversed":
        mesh.invert()
    if defect == "corrupt":
        files[1].write_text("Not an STL")
    else:
        mesh.export(files[1])
    before = files[1].read_bytes()
    result = invoke(files)
    assert result.exit_code == 1, (result.output, result.exception)
    assert not json.loads(files[2].read_text())["passed"]
    assert files[1].read_bytes() == before


@pytest.mark.parametrize("size", [(13, 18, 24), (12, 19, 24)])
def test_wrong_required_dimensions(files, size):
    assert invoke(files, size=size).exit_code == 1
    assert not json.loads(files[2].read_text())["checks"]["required_native_size"]


@pytest.mark.parametrize("size", [(0, 18, 24), (float("nan"), 18, 24), (float("inf"), 18, 24)])
def test_invalid_requirements_do_not_write(files, size):
    assert invoke(files, size=size).exit_code == 2
    assert not files[2].exists()


def test_report_cannot_replace_source(files):
    before = files[1].read_bytes()
    assert invoke((files[0], files[1], files[1])).exit_code == 2
    assert files[1].read_bytes() == before
