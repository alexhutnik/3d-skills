"""Run a small OCS experiment without an editor window. Use uv run."""

import hashlib
import json
import selectors
import subprocess
import time
import uuid
from pathlib import Path


class Session:
    def __init__(self, executable, output):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.log = (self.output / "requests.jsonl").open("w")
        self.stderr = (self.output / "stderr.log").open("w")
        self.process = subprocess.Popen(
            [str(executable), "--serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr,
            text=True,
            bufsize=1,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.state = {}
        self.banner = self.receive()
        if not self.banner.get("ready"):
            raise RuntimeError(self.banner)

    def receive(self, timeout=30):
        while not self.selector.select(timeout):
            if self.process.poll() is not None:
                raise RuntimeError(f"OCS stopped: {self.process.returncode}")
            self.log.write(
                json.dumps(
                    {"observation": "OCS process remains live. Waiting for the same reply; no mutation was replayed."}
                )
                + "\n"
            )
            self.log.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"OCS stopped: {self.process.poll()}")
        return json.loads(line)

    def call(self, op, *, allow_wait=False, **parameters):
        request = {"protocol": 1, "op": op, "request_id": str(uuid.uuid4()), **parameters}
        if "document_id" in self.state:
            request["document_id"] = self.state["document_id"]
        if op not in {"state", "capabilities", "query", "measure", "audit", "commands", "records"}:
            if "revision" in self.state:
                request["revision"] = self.state["revision"]
        started = time.monotonic()
        self.log.write(json.dumps({"request": request}) + "\n")
        self.log.flush()
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        response = self.receive()
        self.log.write(json.dumps({"response": response, "seconds": time.monotonic() - started}) + "\n")
        self.log.flush()
        state = response.get("state", response)
        if "document_id" in state:
            self.state.update(state)
        if not response.get("ok"):
            raise RuntimeError(response)
        if op == "save_verified":
            saved = response.get("result", {})
            path = Path(parameters["path"])
            if not saved.get("verified") or not path.is_file():
                raise RuntimeError("Verified save did not produce a verified file")
            data = path.read_bytes()
            if len(data) != saved["bytes"] or hashlib.sha256(data).hexdigest() != saved["sha256"]:
                raise RuntimeError("Saved file does not match the OCS verification response")
        if not allow_wait and response.get("status") in {"waiting_input", "running", "accepted"}:
            raise RuntimeError(f"Operation needs follow-up: {response}")
        return response

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.selector.close()
        self.log.close()
        self.stderr.close()
