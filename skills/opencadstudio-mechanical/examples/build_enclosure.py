"""Build the console through OCS commands without an editor. Use uv run."""

import typer
from typing import Annotated
from types import SimpleNamespace
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ocs_session import Session
from mechanical import create, solids, save_stage


def subtract(session, base, cutters):
    session.call("select", handles=[base])
    session.call("start", cmd="SUBTRACT", allow_wait=True)
    session.call("select", handles=cutters, allow_wait=True)
    session.call("input", kind="selection", allow_wait=True)
    session.call("input", kind="enter")
    if any(entity["handle"] in cutters for entity in solids(session)):
        raise RuntimeError("OCS did not consume the cutters")
    return base


def fillet(session, handle, radius, points, chain=False):
    before = session.state["revision"]
    session.call("select", handles=[handle])
    session.call("start", cmd="FILLETEDGE", allow_wait=True)
    session.call("input", kind="token", text="R", allow_wait=True)
    session.call("input", kind="text", text=str(radius), allow_wait=True)
    if chain:
        session.call("input", kind="token", text="C", allow_wait=True)
    for point in points:
        session.call("input", kind="entity", handle=handle, point=point, allow_wait=True)
    session.call("input", kind="enter", allow_wait=True)
    session.call("input", kind="enter")
    if session.state["revision"] <= before:
        raise RuntimeError("Fillet command finished without changing the document")


def union(session, handles):
    session.call("select", handles=handles)
    session.call("run", cmd="UNION")
    remaining = solids(session)
    if len(remaining) != 1:
        raise RuntimeError("Union did not produce one solid")
    return remaining[0]["handle"]


def build(session, p):
    fw, fh, fd = (p[name] for name in ["FaceplateWidth", "FaceplateHeight", "FaceplateDepth"])
    bw = p["RearBodyWidth"] - 2 * p["RearMountingClearance"]
    bh = p["RearBodyHeight"] - 2 * p["RearMountingClearance"]
    bd, wall = p["RearBodyDepth"], p["MinimumWallThickness"]
    face = create(session, f"BOX {-fw / 2},{-fh / 2},0 {fw / 2},{fh / 2},0 {fd}")
    fillet(
        session,
        face,
        p["FaceplateCornerRadius"],
        [[x, y, fd / 2] for x in [-fw / 2, fw / 2] for y in [-fh / 2, fh / 2]],
    )
    save_stage(session, "01-rounded-face")
    rear = create(session, f"BOX {-bw / 2},{-bh / 2},{-bd} {bw / 2},{bh / 2},{-bd} {bd}")
    cavity = create(
        session, f"BOX {-bw / 2 + wall},{-bh / 2 + wall},{-bd - 1} {bw / 2 - wall},{bh / 2 - wall},{-bd - 1} {bd + 1}"
    )
    subtract(session, rear, [cavity])
    body = union(session, [face, rear])
    save_stage(session, "02-shell")
    count = int(p["NumberOfConnectorAssemblies"])
    if count not in {1, 2}:
        raise ValueError("Connector count must be one or two")
    xs = [0] if count == 1 else [-p["ConnectorHorizontalSpacing"] / 2, p["ConnectorHorizontalSpacing"] / 2]
    recess_z = fd - p["FlangeRecessDepth"] - p["AdhesiveBondLineAllowance"]
    collar_z = recess_z - p["RearCollarLength"] - p["RearCollarAxialClearance"]
    cutters = []
    for x in xs:
        cutters.append(create(session, f"CYLINDER {x},0,-1 {p['BarrelThroughHoleDiameter'] / 2} {fd + 2}"))
        cutters.append(
            create(
                session,
                f"CYLINDER {x},0,{collar_z} {(p['RearCollarDiameter'] + p['RearCollarClearance']) / 2} {fd - collar_z + 1}",
            )
        )
        cutters.append(
            create(
                session,
                f"CYLINDER {x},0,{recess_z} {(p['FlangeOuterDiameter'] + p['FlangeInsertionClearance']) / 2} {fd - recess_z + 1}",
            )
        )
    subtract(session, body, cutters)
    save_stage(session, "03-console")
    (session.output / "parameters.json").write_text(json.dumps(p, indent=2) + "\n")
    limits = {
        "omitted_edge_rounds": {
            name: p[name] for name in ["ExteriorEdgeRadius", "CableExitRadius"] if p.get(name, 0) > 0
        },
        "reason": "The tested OCS fillet command refuses curved edges. The functional model retains the vertical corner rounds only.",
        "parameter_editing": "Use this Python recipe for coordinated changes. Native solid history also permits individual operand edits.",
    }
    (session.output / "limits.json").write_text(json.dumps(limits, indent=2) + "\n")


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(
    output: Path,
    parameters: Annotated[Path, typer.Option()],
    executable: Annotated[Path, typer.Option()] = Path(
        "/Applications/OpenCADStudio.app/Contents/MacOS/OpenCADStudio-App"
    ),
):
    args = SimpleNamespace(**locals())
    session = Session(args.executable, args.output)
    try:
        session.call("state")
        session.call("new")
        session.call("run", cmd="INSUNITS 4")
        session.call("run", cmd="SOLIDHIST 1")
        build(session, json.loads(args.parameters.read_text()))
        session.call("close", discard=True)
        session.call("open", path=str(session.output / "03-console.dwg"))
        query = session.call("query", detail="summary")
        if len(query["entities"]) != 1:
            raise ValueError("Native roundtrip changed the body count")
        session.call("measure", handles=[query["entities"][0]["handle"]])
        print(json.dumps({"output": str(session.output), "reopened": True, "mode": session.state.get("mode")}))
    finally:
        session.close()


if __name__ == "__main__":
    app()
