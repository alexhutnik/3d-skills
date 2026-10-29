"""Export named STEP parts to one offline HTML review file."""

import hashlib
import html
import json
import math
import re
from importlib.metadata import distribution, version
from pathlib import Path
from typing import Annotated

import k3d
import numpy as np
import typer
from rich.console import Console
from show_scene import load_scene

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
console = Console()


def playback_controls():
    """Attach controls to K3D's existing snapshot without external assets."""
    return """
const play = document.getElementById('review-play');
const reset = document.getElementById('review-reset');
const record = document.getElementById('review-record');
const seek = document.getElementById('review-seek');
const duration = document.getElementById('review-duration');
const status = document.getElementById('review-status');
const download = document.getElementById('review-download');
let position = 0, running = false, previous = null, recorder = null, stream = null, frame = null, epoch = 0;
let downloadUrl = null;
let recordingCanvas = null, recordingContext = null;
const world = K3DInstance.getWorld();
const motion = Object.values(world.ObjectsListJson).map(object => {
    const part = K3DInstance.parameters.customData.parts.find(part => part.name === object.name);
    return {id: object.id, offset: part ? part.explode_mm : [0, 0, 0]};
});
const ease = x => x * x * (3 - 2 * x);
function showPosition(value) {
    position = Math.max(0, Math.min(1, value));
    // Hold, separate, hold, assemble, hold. Both motions have gentle starts and stops.
    const t = position * 12;
    const separation = t < 1 ? 0 : t < 5 ? ease((t - 1) / 4) :
        t < 7 ? 1 : t < 11 ? 1 - ease((t - 7) / 4) : 0;
    // Move the existing meshes. setTime reloads their geometry on every frame.
    motion.forEach(({id, offset}) => {
        const mesh = world.ObjectsById[id];
        if (mesh) mesh.position.set(...offset.map(value => value * separation));
    });
    K3DInstance.parameters.time = separation;
    seek.value = position;
    seek.setAttribute('aria-valuetext', `${Math.round(position * 100)} percent`);
    return world.render(true).then(() => {
        if (recordingContext) {
            recordingContext.fillStyle = '#f4f5f7';
            recordingContext.fillRect(0, 0, recordingCanvas.width, recordingCanvas.height);
            recordingContext.drawImage(world.renderer.domElement, 0, 0);
        }
    });
}
function setRunning(value) {
    cancelAnimationFrame(frame);
    epoch++;
    running = value;
    previous = null;
    play.textContent = running ? 'Pause' : 'Play';
    const token = epoch;
    if (running) frame = requestAnimationFrame(now => tick(now, token));
}
async function tick(now, token) {
    if (!running || token !== epoch) return;
    if (previous !== null) await showPosition(position + (now - previous) / (Number(duration.value) * 1000));
    if (!running || token !== epoch) return;
    previous = now;
    if (position >= 1) {
        setRunning(false);
        if (recorder && recorder.state === 'recording') {
            // Let captureStream receive the final assembled frame before stopping.
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            if (recorder.state === 'recording') recorder.stop();
        }
        else status.textContent = 'Playback complete.';
    } else frame = requestAnimationFrame(now => tick(now, token));
}
play.onclick = () => {
    if (position >= 1) showPosition(0);
    setRunning(!running);
};
reset.onclick = () => { setRunning(false); showPosition(0); status.textContent = 'Ready.'; };
seek.oninput = () => { setRunning(false); showPosition(Number(seek.value)); };
function recordingControls(active) {
    [play, reset, seek, duration, record].forEach(control => control.disabled = active);
    K3DInstance.setCameraLock(active);
}
function releaseStream() {
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    recordingCanvas = recordingContext = null;
    recordingControls(false);
}
record.onclick = async () => {
    setRunning(false);
    await showPosition(0);
    download.hidden = true;
    if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
    try {
        const canvas = document.querySelector('#canvasTarget canvas');
        if (!canvas || !canvas.captureStream || !window.MediaRecorder)
            throw new Error('This browser cannot record the viewer. Use Chrome or Edge.');
        const mimeType = ['video/mp4;codecs=avc1.42002A', 'video/webm;codecs=vp9',
            'video/webm;codecs=vp8', 'video/webm'].find(type => MediaRecorder.isTypeSupported(type));
        if (!mimeType) throw new Error('This browser has no supported video format.');
        recordingControls(true);
        // Draw the assembled pose before capture begins.
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        // Composite the transparent WebGL canvas onto an opaque background.
        recordingCanvas = document.createElement('canvas');
        recordingCanvas.width = canvas.width;
        recordingCanvas.height = canvas.height;
        recordingContext = recordingCanvas.getContext('2d', {alpha: false});
        await showPosition(0);
        stream = recordingCanvas.captureStream(60);
        recorder = new MediaRecorder(stream, {mimeType, videoBitsPerSecond: 12000000});
        const chunks = [];
        recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
        recorder.onstop = () => {
            releaseStream();
            if (!chunks.length) { status.textContent = 'The browser produced no video. Try again.'; return; }
            const type = recorder.mimeType;
            const extension = type.startsWith('video/mp4') ? 'mp4' : 'webm';
            downloadUrl = URL.createObjectURL(new Blob(chunks, {type}));
            download.href = downloadUrl;
            download.download = `assembly-review.${extension}`;
            download.textContent = `Save video (.${extension})`;
            download.hidden = false;
            status.textContent = 'Video ready. Select Save video.';
        };
        recorder.onerror = () => {
            setRunning(false);
            releaseStream();
            status.textContent = 'Recording failed. Try again.';
        };
        recorder.start();
        status.textContent = 'Recording. Keep this tab visible until the video is ready.';
        setRunning(true);
    } catch (error) {
        releaseStream();
        status.textContent = error.message;
    }
};
// A hidden tab cannot supply smooth frames. Reject an interrupted recording.
document.addEventListener('visibilitychange', () => {
    if (document.hidden && running) {
        setRunning(false);
        if (recorder && recorder.state === 'recording') {
            recorder.onstop = () => {
                releaseStream();
                status.textContent = 'Recording stopped because the tab was hidden. Record again.';
            };
            recorder.stop();
        }
    }
});
[play, reset, seek, duration, record].forEach(control => control.disabled = false);
status.textContent = 'Ready. One cycle separates the parts and assembles them again.';
"""


def make_review(scene, title, tolerance=0.05, rotate_speed=3.0):
    """Keep CAD input unchanged. Tessellate only for display."""
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("The mesh tolerance must be positive and finite")
    if not math.isfinite(rotate_speed) or rotate_speed <= 0:
        raise ValueError("The rotation speed must be positive and finite")
    scene = Path(scene).resolve()
    shapes, parts = load_scene(scene)
    plot = k3d.plot(
        snapshot_type="full",
        background_color=0xF4F5F7,
        grid_visible=False,
        axes_helper=0,
        camera_auto_fit=False,
        camera_up_axis="z",
        time_interpolation=True,
        camera_fov=45,
        menu_visibility=True,
        camera_rotate_speed=rotate_speed,
    )
    report = {
        "title": title,
        "units": "mm",
        "mesh_tolerance_mm": tolerance,
        "camera_rotate_speed": rotate_speed,
        "scene_sha256": hashlib.sha256(scene.read_bytes()).hexdigest(),
        "versions": {name: version(name) for name in ("build123d", "k3d")},
        "parts": [],
    }
    bounds = []
    for shape, part in zip(shapes, parts):
        color = part.get("color", "#6f8192" if part["role"] == "printed" else "#d7a95b")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"Use a six-digit hex color for {part['name']}")
        vertices, triangles = shape.tessellate(tolerance, angular_tolerance=0.1)
        vertices = np.asarray([tuple(v) for v in vertices], dtype=np.float32)
        triangles = np.asarray(triangles, dtype=np.uint32)
        if vertices.size == 0 or triangles.size == 0 or not np.isfinite(vertices).all():
            raise ValueError(f"Invalid display mesh for {part['name']}")
        mesh = k3d.mesh(
            vertices, triangles, color=int(color[1:], 16), name=part["name"], group=part["role"], flat_shading=False
        )
        offset = np.asarray(part.get("explode_mm", [0, 0, 0]), dtype=np.float32)
        if np.any(offset):
            assembled = np.eye(4, dtype=np.float32)
            exploded = assembled.copy()
            exploded[:3, 3] = offset
            mesh.model_matrix = {"0": assembled, "1": exploded}
        plot += mesh
        box = shape.bounding_box()
        lower, upper = np.array(tuple(box.min)), np.array(tuple(box.max))
        bounds.extend((lower, upper, lower + offset, upper + offset))
        source = (scene.parent / part["step"]).resolve()
        report["parts"].append(
            {
                "name": part["name"],
                "role": part["role"],
                "source": source.name,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "solids": len(shape.solids()),
                "triangles": len(triangles),
                "size_mm": list(box.size),
                "assembled_bounds_mm": [list(lower), list(upper)],
                "explode_mm": offset.tolist(),
            }
        )
    bounds = np.asarray(bounds)
    center = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
    radius = np.linalg.norm(bounds.max(axis=0) - bounds.min(axis=0)) / 2
    direction = np.array([1.2, -1.5, 1.1])
    direction /= np.linalg.norm(direction)
    eye = center + direction * radius / math.sin(math.radians(22.5)) * 1.15
    plot.camera = [*eye, *center, 0, 0, 1]
    report["review_id"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()[:12]
    plot.custom_data = report
    document = plot.get_snapshot()
    safe_title = html.escape(title)
    rows = "".join(
        f"<li><strong>{html.escape(p['name'])}</strong> · {p['role']}"
        f"<br><span>{' × '.join(f'{v:.2f}' for v in p['size_mm'])} mm</span></li>"
        for p in report["parts"]
    )
    header = f"""<header><div class="eyebrow">3D REVIEW · OFFLINE FILE</div>
<h1>{safe_title}</h1>
<p>Drag to rotate. Scroll to zoom. Open Objects to hide a part.</p>
<div class="playback" role="group" aria-label="Assembly playback">
<button id="review-play" disabled>Play</button>
<button id="review-reset" disabled>Reset</button>
<label for="review-duration">Cycle</label><select id="review-duration" disabled>
<option value="8">8 seconds</option><option value="12" selected>12 seconds</option>
<option value="20">20 seconds</option></select>
<label class="timeline">Timeline <input id="review-seek" type="range" min="0" max="1" step="0.001" value="0" disabled></label>
<button id="review-record" disabled>Record video</button>
<a id="review-download" hidden>Save video</a>
<p id="review-status" role="status">Loading the viewer…</p>
</div>
<p>Record video saves the model without the controls. Set the view before recording.</p>
<p>Keep this tab visible. The browser selects MP4 or WebM. The target is 60 frames per second.</p>
<p>For manual separation, open Controls → Animation → time. Set 0 for assembled or 1 for exploded.</p>
<details><summary>Parts and review limits</summary><ul>{rows}</ul>
<p>Dimensions come from the STEP geometry. The display uses a mesh.</p>
<p>Separation shows the assembly. It does not check collisions.</p>
<p>This file contains reference hardware. Do not use it as a print file.</p>
<p>Built with K3D {version("k3d")}. No server or network connection is required.</p>
<p>Review {report["review_id"]} · Display tolerance: {tolerance:g} mm</p>
</details></header>"""
    style = """<style>
body {font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#233449;}
#canvasTarget {isolation:isolate;z-index:0;}
header {position:absolute;z-index:5;top:24px;left:28px;max-width:min(430px,calc(100vw - 64px));
 max-height:calc(100vh - 88px);overflow:auto;
 background:rgba(255,255,255,.94);padding:20px 24px;border:1px solid #dfe4eb;
 border-radius:14px;box-shadow:0 8px 32px #21364a10;}
.eyebrow {font-size:10px;letter-spacing:2px;color:#62778d;font-weight:700;}
h1 {font-size:23px;letter-spacing:-.5px;margin:8px 0 14px;}
p {font-size:12px;line-height:1.6;margin:4px 0;}
details {margin-top:12px;font-size:12px;} summary {cursor:pointer;color:#37698c;}
pre {white-space:pre-wrap;font-size:10px;}
ul {padding-left:18px;} li {margin:9px 0;} li span {color:#62778d;}
.playback {display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0;}
button,select,.playback a {font:inherit;font-size:12px;border:1px solid #b7c6d4;
 border-radius:6px;padding:7px 10px;background:#fff;color:#233449;}
button {cursor:pointer;} button:disabled {cursor:wait;opacity:.5;}
.playback label {font-size:12px;} .timeline {display:flex;align-items:center;gap:8px;width:100%;}
.timeline input {flex:1;min-width:0;} #review-status {width:100%;}
@media(max-width:750px) {header {top:12px;left:12px;padding:12px;max-width:45vw;}
h1 {font-size:17px;} header p {font-size:10px;}}
</style>"""
    document = re.sub(r"<title>.*?</title>", lambda _: f"<title>{safe_title}</title>", document, count=1)
    package = distribution("k3d")
    notices = []
    for entry in package.files:
        if str(entry).endswith(
            ("licenses/LICENSE.txt", "static/standalone.js.LICENSE.txt", "static/require.js.LICENSE.txt")
        ):
            notices.append(Path(package.locate_file(entry)).read_text())
    licenses = "<details><summary>Viewer licenses</summary><pre>"
    licenses += html.escape("\n\n".join(notices)) + "</pre></details>"
    header = header.replace("</header>", licenses + "</header>")
    document = document.replace("</head>", style + "</head>", 1)
    document = document.replace("<body>", "<body>" + header, 1)
    hook = "K3DInstance.then(function(K3DInstance) {"
    if hook not in document:
        raise ValueError("The K3D snapshot has no playback initialization hook")
    document = document.replace(hook, hook + playback_controls(), 1)
    return re.sub(r"(?m)^[ \t]+$", "", document), report


@app.command()
def main(
    scene: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Argument(dir_okay=False)],
    title: Annotated[str, typer.Option(help="The title shown in the review.")] = "Assembly review",
    tolerance: Annotated[float, typer.Option(help="Display mesh tolerance in mm.", min=0.001)] = 0.05,
    rotate_speed: Annotated[float, typer.Option(help="Mouse rotation speed multiplier.", min=0.01)] = 3.0,
):
    """Create one HTML file with the viewer and all display geometry embedded."""
    if output.suffix.lower() != ".html":
        raise typer.BadParameter("The output must be an HTML file", param_hint="output")
    if scene.resolve() in (output.resolve(), output.with_suffix(".review.json").resolve()):
        raise typer.BadParameter("The output must not replace the scene file")
    try:
        with console.status("Create the display meshes and offline viewer…"):
            document, report = make_review(scene, title, tolerance, rotate_speed)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(document)
        output.with_suffix(".review.json").write_text(json.dumps(report, indent=2) + "\n")
    except (ValueError, OSError) as error:
        console.print(f"[red]Export failed:[/red] {error}", highlight=False)
        raise typer.Exit(1) from error
    console.print(f"Saved {output} ({output.stat().st_size / 1_000_000:.2f} MB)", markup=False)


if __name__ == "__main__":
    app()
