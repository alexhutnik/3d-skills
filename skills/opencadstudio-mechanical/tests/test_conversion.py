import json
import sys
from pathlib import Path

import pytest
import trimesh
from typer.testing import CliRunner

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from convert_acis import app as convert
from check_mesh import app as check


def convert_args(output):
    return [
        str(SKILL / "tests/fixtures/box.sat"),
        str(output),
        "--source-unit-mm",
        "1",
        "--size",
        "20",
        "30",
        "10",
        "--volume",
        "6000",
    ]


def test_real_sat_roundtrip_and_existing_output(tmp_path):
    output = tmp_path / "converted"
    result = CliRunner().invoke(convert, convert_args(output))
    assert result.exit_code == 0, (result.output, result.exception)
    report = json.loads((output / "conversion.json").read_text())
    assert report["step_roundtrip_passed"]
    assert report["size_mm"] == pytest.approx([20, 30, 10])
    before = (output / "part.stl").read_bytes()
    assert CliRunner().invoke(convert, convert_args(output)).exit_code == 2
    assert (output / "part.stl").read_bytes() == before


@pytest.mark.parametrize(
    "option,value", [("--source-unit-mm", "10"), ("--volume", "7000"), ("--volume", "nan"), ("--source-unit-mm", "0")]
)
def test_reject_bad_conversion(tmp_path, option, value):
    output = tmp_path / "converted"
    args = convert_args(output)
    args[args.index(option) + 1] = value
    result = CliRunner().invoke(convert, args)
    assert result.exit_code != 0
    assert not output.exists()


def test_corrupt_sat_does_not_write(tmp_path):
    source = tmp_path / "broken.sat"
    source.write_text("Not SAT geometry")
    args = convert_args(tmp_path / "output")
    args[0] = str(source)
    assert CliRunner().invoke(convert, args).exit_code != 0
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("defect", [None, "open", "size", "volume", "reversed"])
def test_mesh_checks(tmp_path, defect):
    mesh = trimesh.creation.box(extents=[20, 30, 10])
    if defect == "open":
        mesh.update_faces(range(len(mesh.faces) - 1))
    elif defect == "reversed":
        mesh.invert()
    source, report = tmp_path / "box.stl", tmp_path / "nested/check.json"
    mesh.export(source)
    before = source.read_bytes()
    args = [
        str(source),
        "--size",
        "21" if defect == "size" else "20",
        "30",
        "10",
        "--volume",
        "7000" if defect == "volume" else "6000",
        "--report",
        str(report),
    ]
    result = CliRunner().invoke(check, args)
    assert result.exit_code == (0 if defect is None else 1), (result.output, result.exception)
    assert json.loads(report.read_text())["passed"] == (defect is None)
    assert source.read_bytes() == before


def test_mesh_report_cannot_replace_input(tmp_path):
    source = tmp_path / "box.stl"
    trimesh.creation.box().export(source)
    before = source.read_bytes()
    result = CliRunner().invoke(check, [str(source), "--size", "1", "1", "1", "--volume", "1", "--report", str(source)])
    assert result.exit_code == 2
    assert source.read_bytes() == before
