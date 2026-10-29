# Browser review workflows

Set `SKILL_DIR` to this installed skill's absolute path. Follow symbolic links.
Set `PLUGIN_DIR` to the directory two levels above that folder. Keep the complete plugin installed.
Keep output files in the user project. Use the locked environment:

```sh
PLUGIN_DIR="$(cd "$SKILL_DIR/../.." && pwd -P)"
uv sync --project "$PLUGIN_DIR" --locked --no-dev
uv run --project "$PLUGIN_DIR" --locked --no-dev python "$SKILL_DIR/scripts/export_review.py" /absolute/project/scene.json /absolute/project/review.html
```

Open the HTML file in a browser. It embeds the viewer and display meshes.
The adjacent `.review.json` records source hashes, dimensions, roles, and library versions.
The HTML file does not need the JSON report to open.

- Drag to rotate. Scroll to zoom.
- Select **Play** to separate and assemble the parts. Select **Pause** to stop.
- Move **Timeline** to inspect a position. Select **Reset** to return to the assembled position.
- Select an 8, 12, or 20 second cycle.
- Open **Objects** and a part group to change its visibility.
- Open **Controls → Animation** to set the separation directly.

The exporter uses rotation speed `3`. Use `--rotate-speed 2` for a slower response.
Rebuild the file after changing the speed or geometry.
The viewer does not provide exact CAD measurements. Its dimensions come from the source STEP files.
An exploded view changes display positions only. It does not check collisions.

## Video

Select **Record video** for a browser recording. Keep the tab visible until **Save video** appears.
The recording uses the current camera and visible parts. It excludes the controls.
The browser selects MP4 or WebM. The actual frame rate depends on the browser and computer.

For a fixed frame rate, install FFmpeg and Playwright Chromium, then run:

```sh
uv run --project "$PLUGIN_DIR" --locked --no-dev playwright install chromium
uv run --project "$PLUGIN_DIR" --locked --no-dev python "$SKILL_DIR/scripts/render_video.py" /absolute/project/review.html /absolute/project/review.mp4
```

The defaults are 12 seconds, 1920 × 1080 pixels, and 60 frames per second.
Use `--seconds`, `--fps`, `--width`, and `--height` to change them.
The script stages its output. A failed render must not replace an existing video.

## Live OCP Viewer

Use a live server when Python must send changed geometry or calculate exact results.
Start the server in a tool session that remains alive:

```sh
uv run --project "$PLUGIN_DIR" --locked --no-dev python -m ocp_viewer --host 127.0.0.1 --port 3939 --theme light
```

Open `http://127.0.0.1:3939/viewer`, then send the scene:

```sh
uv run --project "$PLUGIN_DIR" --locked --no-dev python "$SKILL_DIR/scripts/show_scene.py" /absolute/project/scene.json --motion
```

Use `--check-only` to validate the scene without contacting a server.
A newly opened tab can show only the OCP logo until Python sends the scene again.
Each STEP input forms one rigid display group.
Use Clip for sections. Confirm the source of a measurement before treating it as exact.
Stop only the server started for the current task.

## Tests

Run the independent tests from this skill folder:

```sh
PLUGIN_DIR="$(cd "$SKILL_DIR/../.." && pwd -P)"
uv sync --project "$PLUGIN_DIR" --locked
uv run --project "$PLUGIN_DIR" --locked playwright install chromium
uv run --project "$PLUGIN_DIR" --locked pytest "$SKILL_DIR/tests"
```

The tests generate a synthetic assembly and use an offline browser context.
They check rendering, reopening, visibility, rotation, separation, playback, and browser recording.
Software rendering can differ from the user's graphics driver. Inspect a generated review before delivery.

Sources: [K3D snapshots](https://k3d-jupyter.org/user/snapshots.html),
[K3D time series](https://k3d-jupyter.org/user/time.html),
[OCP Viewer](https://bernhard-42.github.io/ocp_viewer_docs/).
