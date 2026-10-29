import hashlib
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ocs_session import Session


def session_with(response):
    session = Session.__new__(Session)
    session.state = {"document_id": "drawing", "revision": 4}
    session.log = io.StringIO()
    session.process = SimpleNamespace(stdin=io.StringIO())
    session.receive = lambda: response
    return session


def test_mutation_uses_revision_and_tracks_result():
    session = session_with({"ok": True, "state": {"document_id": "drawing", "revision": 5}})
    session.call("run", cmd="BOX 0,0,0 10,10,0 10")
    request = json.loads(session.process.stdin.getvalue())
    assert request["revision"] == 4
    assert request["document_id"] == "drawing"
    assert request["request_id"]
    assert session.state["revision"] == 5


@pytest.mark.parametrize("status", ["running", "waiting_input", "accepted"])
def test_incomplete_operation_is_not_success_or_replayed(status):
    session = session_with({"ok": True, "status": status})
    with pytest.raises(RuntimeError, match="follow-up"):
        session.call("run", cmd="FILLETEDGE")
    assert len(session.process.stdin.getvalue().splitlines()) == 1


def test_save_checks_actual_bytes(tmp_path):
    path = tmp_path / "part.dwg"
    path.write_bytes(b"saved drawing")
    session = session_with(
        {
            "ok": True,
            "result": {
                "verified": True,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            },
        }
    )
    session.call("save_verified", path=str(path))
    path.write_bytes(b"changed drawing")
    with pytest.raises(RuntimeError, match="does not match"):
        session.call("save_verified", path=str(path))


def test_failed_request_propagates():
    session = session_with({"ok": False, "error": "unsupported"})
    with pytest.raises(RuntimeError, match="unsupported"):
        session.call("query")


def test_snapshot_uses_separate_session_and_preserves_input(tmp_path, monkeypatch):
    import snapshot_native
    from typer.testing import CliRunner

    source, output = tmp_path / "source.dwg", tmp_path / "snapshot"
    source.write_bytes(b"Original drawing")
    calls = []

    class FakeSession:
        def __init__(self, executable, target):
            self.output = target
            target.mkdir()

        def call(self, op, **kwargs):
            calls.append((op, kwargs))
            if op == "query":
                return {
                    "entities": [
                        {
                            "type": "3D Solid",
                            "handle": "1",
                            "properties": {"acis_data": {"is_binary": False, "sat_data": "Synthetic SAT"}},
                        }
                    ]
                }
            return {}

        def close(self):
            calls.append(("close", {}))

    monkeypatch.setattr(snapshot_native, "Session", FakeSession)
    result = CliRunner().invoke(snapshot_native.app, [str(source), str(output)])
    assert result.exit_code == 0, result.output
    assert source.read_bytes() == b"Original drawing"
    assert (output / "part.sat").read_text() == "Synthetic SAT"
    assert ("open", {"path": str(source.resolve())}) in calls
    assert calls[-1][0] == "close"


def test_primitive_creation_requires_exactly_one_new_solid():
    from mechanical import create

    class FakeSession:
        def __init__(self, new_entities):
            self.entities = [{"type": "3D Solid", "handle": "old"}]
            self.new_entities = new_entities

        def call(self, op, **kwargs):
            if op == "run":
                self.entities += self.new_entities
            return {"entities": self.entities}

    assert create(FakeSession([{"type": "3D Solid", "handle": "new"}]), "BOX") == "new"
    with pytest.raises(RuntimeError, match="one new solid"):
        create(FakeSession([]), "BOX")
