"""Test Boolean operations in a private, headless OCS session. Use uv run."""

import json


def solids(session):
    result = session.call("query", detail="full")
    return [entity for entity in result["entities"] if entity["type"] == "3D Solid"]


def create(session, command):
    before = {entity["handle"] for entity in solids(session)}
    session.call("run", cmd=command)
    added = [entity["handle"] for entity in solids(session) if entity["handle"] not in before]
    if len(added) != 1:
        raise RuntimeError(f"Expected one new solid: {added}")
    return added[0]


def subtract(session, base, cutters):
    session.call("select", handles=[base])
    session.call("start", cmd="SUBTRACT", allow_wait=True)
    session.call("select", handles=cutters, allow_wait=True)
    session.call("input", kind="selection", allow_wait=True)
    session.call("input", kind="enter")
    remaining = solids(session)
    if len(remaining) != 1:
        raise RuntimeError(f"Expected one solid after subtraction: {len(remaining)}")
    return remaining[0]["handle"]


def save_stage(session, name):
    entities = solids(session)
    if len(entities) != 1:
        raise RuntimeError("Expected one solid")
    entity = entities[0]
    measurement = session.call("measure", handles=[entity["handle"]])
    (session.output / f"{name}.sat").write_text(entity["properties"]["acis_data"]["sat_data"])
    (session.output / f"{name}-measure.json").write_text(json.dumps(measurement, indent=2) + "\n")
    session.call("save_verified", path=str(session.output / f"{name}.dwg"), target_format="dwg", overwrite=False)
