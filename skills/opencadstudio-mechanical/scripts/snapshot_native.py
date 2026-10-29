"""Read a drawing through a private OCS session. Do not change the source."""

import typer
from typing import Annotated
from types import SimpleNamespace
import json
from pathlib import Path

from ocs_session import Session


app = typer.Typer(pretty_exceptions_enable=False)


@app.command()
def main(
    source: Path,
    output: Path,
    executable: Annotated[Path, typer.Option()] = Path(
        "/Applications/OpenCADStudio.app/Contents/MacOS/OpenCADStudio-App"
    ),
):
    args = SimpleNamespace(**locals())
    session = Session(args.executable, args.output)
    try:
        session.call("state")
        session.call("open", path=str(args.source.resolve()))
        result = session.call("query", detail="full")
        solids = [entity for entity in result["entities"] if entity["type"] == "3D Solid"]
        if len(solids) != 1:
            raise ValueError(f"Expected one solid, got {len(solids)}")
        entity = solids[0]
        acis = entity["properties"]["acis_data"]
        if acis["is_binary"]:
            if not acis["sab_data"]:
                raise ValueError("Native solid has no binary ACIS data")
            (session.output / "part.sab").write_bytes(bytes(acis["sab_data"]))
            session.call(
                "save_verified",
                path=str(session.output / "ascii-2000.dxf"),
                target_format="dxf",
                target_version="2000",
                overwrite=False,
            )
            session.call("open", path=str(session.output / "ascii-2000.dxf"))
            result = session.call("query", detail="full")
            if len(result["entities"]) != 1:
                raise ValueError("Legacy copy changed entity count")
            entity = result["entities"][0]
            acis = entity["properties"]["acis_data"]
            if acis["is_binary"] or not acis["sat_data"]:
                raise ValueError("Legacy copy did not expose ASCII SAT")
            (session.output / "part.sat").write_text(acis["sat_data"])
        else:
            if not acis["sat_data"]:
                raise ValueError("Native solid has no ASCII ACIS data")
            (session.output / "part.sat").write_text(acis["sat_data"])
        measured = session.call("measure", handles=[entity["handle"]])
        (session.output / "measure.json").write_text(json.dumps(measured, indent=2) + "\n")
        print(json.dumps({"source": str(args.source), "output": str(session.output), "solid_count": 1}))
    finally:
        session.close()


if __name__ == "__main__":
    app()
