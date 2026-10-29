"""Check the offline artifact, not a running viewer server."""

import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Cylinder, export_step
from PIL import Image
from playwright.sync_api import sync_playwright
from typer.testing import CliRunner

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from export_review import app, make_review


def test_geometry_metadata_and_source_preservation(tmp_path):
    step = tmp_path / "part.step"
    export_step(Box(12, 18, 24), step)
    before = hashlib.sha256(step.read_bytes()).hexdigest()
    scene = tmp_path / "scene.json"
    scene.write_text(
        json.dumps(
            {
                "units": "mm",
                "parts": [
                    {
                        "name": "part",
                        "role": "printed",
                        "step": step.name,
                        "rotation_deg": [0, 0, 90],
                        "translation_mm": [20, 30, 40],
                    }
                ],
            }
        )
    )
    document, report = make_review(scene, "Test <part>")
    part = report["parts"][0]
    assert part["size_mm"] == pytest.approx([18, 12, 24])
    assert part["assembled_bounds_mm"][0] == pytest.approx([11, 24, 28])
    assert part["assembled_bounds_mm"][1] == pytest.approx([29, 36, 52])
    assert part["sha256"] == before == hashlib.sha256(step.read_bytes()).hexdigest()
    assert "<title>Test &lt;part&gt;</title>" in document
    assert "<title>Test <part></title>" not in document
    result = CliRunner().invoke(app, [str(scene), str(tmp_path / "bad.html"), "--tolerance", "0"])
    assert result.exit_code == 2
    assert not (tmp_path / "bad.html").exists()


def image_pixels(page, path):
    page.wait_for_timeout(500)
    shot = page.screenshot(path=str(path))
    # Exclude the fixed header and control panel from the image comparison.
    return np.asarray(Image.open(io.BytesIO(shot)).convert("RGB"))[220:900, 440:1180]


def changed_pixels(first, second):
    return int(np.count_nonzero(np.max(np.abs(first.astype(int) - second.astype(int)), axis=2) > 15))


@pytest.fixture
def review_files(tmp_path):
    housing = Box(90, 65, 12) - Box(76, 51, 10).translate((0, 0, 4))
    export_step(housing, tmp_path / "housing.step")
    export_step(Cylinder(10, 24), tmp_path / "connector.step")
    scene = tmp_path / "scene.json"
    scene.write_text(
        json.dumps(
            {
                "units": "mm",
                "parts": [
                    {"name": "housing", "role": "printed", "step": "housing.step", "color": "#637c99"},
                    {
                        "name": "connector-a",
                        "role": "reference",
                        "step": "connector.step",
                        "translation_mm": [-18, 0, 12],
                        "explode_mm": [0, 0, 50],
                    },
                    {
                        "name": "connector-b",
                        "role": "reference",
                        "step": "connector.step",
                        "translation_mm": [18, 0, 12],
                        "explode_mm": [0, 0, 50],
                    },
                ],
            }
        )
    )
    document, _ = make_review(scene, "Synthetic assembly")
    review = tmp_path / "review.html"
    review.write_text(document)
    return review, tmp_path


@pytest.mark.browser
def test_offline_render_reopen_explode_and_visibility(review_files):
    review, out = review_files
    errors, network = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, offline=True)
        context.on(
            "request",
            lambda request: (
                network.append(request.url) if request.url.startswith(("http:", "https:", "ws:", "wss:")) else None
            ),
        )
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(review.as_uri())
        page.get_by_text("Controls", exact=True).wait_for()
        assembled = image_pixels(page, out / "static-assembled.png")
        background = np.array([244, 245, 247])
        assert np.count_nonzero(np.max(np.abs(assembled.astype(int) - background), axis=2) > 40) > 20000

        for label, content in (("Parts and review limits", "ul"), ("Viewer licenses", "pre")):
            summary = page.get_by_text(label, exact=True)
            details = summary.locator("..")
            summary.click()
            assert details.get_attribute("open") == ""
            assert details.locator(content).is_visible()
            page.screenshot(path=str(out / f"static-{content}-open.png"))
            summary.click()
            assert details.get_attribute("open") is None
            summary.focus()
            summary.press("Enter")
            assert details.locator(content).is_visible()
            summary.press("Space")
            assert details.get_attribute("open") is None

        page.get_by_text("Controls", exact=True).click()
        page.get_by_text("Animation", exact=True).click()
        page.get_by_label("time", exact=True).fill("1")
        page.get_by_label("time", exact=True).press("Enter")
        page.get_by_text("Controls", exact=True).click()
        exploded = image_pixels(page, out / "static-exploded.png")
        assert changed_pixels(assembled, exploded) > 10000

        for label in ("Objects", "printed", "housing"):
            page.get_by_text(label, exact=True).last.click()
        page.get_by_label("visible", exact=True).first.uncheck()
        page.get_by_text("Objects", exact=True).click()
        hidden = image_pixels(page, out / "static-hidden.png")
        assert changed_pixels(exploded, hidden) > 20000

        page.reload()
        page.get_by_text("Controls", exact=True).wait_for()
        reopened = image_pixels(page, out / "static-reloaded.png")
        assert changed_pixels(assembled, reopened) < 1000
        page.mouse.move(800, 600)
        page.mouse.down()
        page.mouse.move(930, 680, steps=12)
        page.mouse.up()
        rotated = image_pixels(page, out / "static-rotated.png")
        assert changed_pixels(reopened, rotated) > 10000

        # A fresh context has no cached document or prior viewer state.
        fresh = browser.new_context(viewport={"width": 1440, "height": 1000}, offline=True)
        fresh.on(
            "request",
            lambda request: (
                network.append(request.url) if request.url.startswith(("http:", "https:", "ws:", "wss:")) else None
            ),
        )
        second = fresh.new_page()
        second.on("pageerror", lambda error: errors.append(str(error)))
        second.goto(review.as_uri())
        second.get_by_text("Controls", exact=True).wait_for()
        second_pixels = image_pixels(second, out / "static-fresh.png")
        assert changed_pixels(assembled, second_pixels) < 1000
        assert not errors, errors
        assert not network, network
        browser.close()


@pytest.mark.browser
def test_playback_and_video_offline(review_files):
    review, out = review_files
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, offline=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(review.as_uri())
        play = page.get_by_role("button", name="Play", exact=True)
        page.wait_for_function("!document.getElementById('review-play').disabled")
        assembled = image_pixels(page, out / "playback-assembled.png")
        seek = page.get_by_label("Timeline", exact=True)
        seek.fill("0.5")
        exploded = image_pixels(page, out / "playback-exploded.png")
        assert changed_pixels(assembled, exploded) > 10000
        page.get_by_role("button", name="Reset", exact=True).click()
        assert float(seek.input_value()) == 0
        page.get_by_label("Cycle", exact=True).select_option("8")
        play.click()
        page.wait_for_function("Number(document.getElementById('review-seek').value) > 0.05")
        page.get_by_role("button", name="Pause", exact=True).click()
        paused = seek.input_value()
        page.wait_for_timeout(300)
        assert seek.input_value() == paused
        play.click()
        page.wait_for_function("document.getElementById('review-seek').value === '1'", timeout=15000)
        assert play.is_enabled()

        page.get_by_role("button", name="Record video", exact=True).click()
        assert play.is_disabled()
        save = page.get_by_role("link", name="Save video", exact=False)
        save.wait_for(timeout=20000)
        assert play.is_enabled()
        with page.expect_download() as pending:
            save.click()
        download = pending.value
        path = out / download.suggested_filename
        download.save_as(path)
        assert path.stat().st_size > 10000
        # Decode the recording in the browser. Check size, duration, and model motion.
        result = page.evaluate("""async () => {
            const video = document.createElement('video');
            video.src = document.getElementById('review-download').href;
            await new Promise((resolve, reject) => {
                video.onloadeddata = resolve; video.onerror = reject;
            });
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth; canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            async function pixels(time) {
                video.currentTime = time;
                await new Promise(resolve => video.onseeked = resolve);
                ctx.drawImage(video, 0, 0);
                return ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            }
            const first = await pixels(0.1), middle = await pixels(4);
            const last = await pixels(video.duration - 0.05);
            let changed = 0, modelPixels = 0, returned = 0;
            for (let i = 0; i < first.length; i += 4) {
                if (Math.abs(first[i] - middle[i]) > 20) changed++;
                if (Math.abs(first[i] - last[i]) > 20) returned++;
                if (first[i] < 200 && first[i + 1] < 200 && first[i + 2] < 200) modelPixels++;
            }
            return {width:video.videoWidth, height:video.videoHeight, changed, modelPixels, returned,
                background:Array.from(first.slice(0, 3))};
        }""")
        assert result["width"] == 1440
        assert result["height"] == 1000
        assert result["changed"] > 10000
        assert result["modelPixels"] > 20000
        assert result["returned"] < 2000
        assert result["background"] == pytest.approx([244, 245, 247], abs=4)
        assert not errors, errors
        browser.close()
