"""Render every animation frame before encoding a constant-rate MP4."""

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import typer
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.progress import track

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
console = Console()


@app.command()
def main(
    review: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Argument(dir_okay=False)],
    seconds: Annotated[int, typer.Option(min=2, max=120)] = 12,
    fps: Annotated[int, typer.Option(min=1, max=60)] = 60,
    width: Annotated[int, typer.Option(min=320, max=3840)] = 1920,
    height: Annotated[int, typer.Option(min=240, max=2160)] = 1080,
):
    """Save one complete cycle. Rendering can take longer than playback."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise typer.BadParameter("Install FFmpeg before rendering video")
    if output.suffix.lower() != ".mp4":
        raise typer.BadParameter("The output must be an MP4 file")
    if width % 2 or height % 2:
        raise typer.BadParameter("The width and height must be even numbers")
    if review.resolve() == output.resolve():
        raise typer.BadParameter("Use a separate output file")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep partial output separate. A failed render must not replace an existing video.
    with TemporaryDirectory(prefix="review-video-", dir=output.parent) as temporary:
        staged = Path(temporary) / "review.mp4"
        log = Path(temporary) / "ffmpeg.log"
        with log.open("w+") as errors, sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--enable-unsafe-swiftshader"])
            context = browser.new_context(viewport={"width": width, "height": height}, offline=True)
            page = context.new_page()
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(review.resolve().as_uri())
            page.wait_for_function("!document.getElementById('review-play').disabled")
            page.add_style_tag(content="header {display:none!important} body {background:#f4f5f7}")
            page.evaluate("async () => (await K3DInstance).setMenuVisibility(false)")
            command = [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-f",
                "image2pipe",
                "-framerate",
                str(fps),
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(staged),
            ]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors)
            try:
                frames = seconds * fps
                for frame in track(range(frames), description="Render the video frames"):
                    # The slider owns the same easing and cycle as interactive playback.
                    page.evaluate(
                        """async value => {
                        const slider = document.getElementById('review-seek');
                        slider.value = value;
                        slider.dispatchEvent(new Event('input'));
                        const plot = await K3DInstance;
                        await plot.getWorld().render(true);
                    }""",
                        frame / (frames - 1),
                    )
                    if page_errors:
                        raise RuntimeError("The viewer failed: " + "; ".join(page_errors))
                    process.stdin.write(page.screenshot(type="png"))
                process.stdin.close()
                if process.wait(timeout=120):
                    errors.seek(0)
                    raise RuntimeError("FFmpeg failed: " + errors.read())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                browser.close()
        staged.replace(output)
    console.print(f"Saved {output}: {width} × {height}, {fps} frames per second, {seconds} seconds", markup=False)


if __name__ == "__main__":
    app()
