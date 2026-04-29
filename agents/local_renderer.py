import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import async_playwright


def _ts(seconds: float) -> str:
    ms = int((seconds - int(seconds)) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render_mermaid_video(plan: Dict[str, Any], product_name: str, output_mp4_path: str, fps: int = 30) -> str:
    async def _run():
        root = Path(__file__).resolve().parents[1]
        tpl = root / "video" / "templates" / "scene_template.html"
        work = root / "output" / "frames"
        work.mkdir(parents=True, exist_ok=True)
        for f in work.glob("*.png"):
            f.unlink(missing_ok=True)

        scenes = plan["scenes"]
        duration_s = int(plan["video"]["duration_s"])
        scene_dur = duration_s / len(scenes)
        total_frames = duration_s * fps

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            await page.goto(tpl.as_uri())

            for frame in range(total_frames):
                t = frame / fps
                idx = min(len(scenes) - 1, int(t // scene_dur))
                scene = scenes[idx]
                scene_graph = scene.get("mermaid_diagram") or scene.get("diagram") or plan.get("mermaid_graph", "")
                payload = {
                    "product": product_name,
                    "sceneIndex": idx,
                    "totalScenes": len(scenes),
                    "title": scene.get("header") or scene.get("title") or "",
                    "subtitle": scene.get("subtitle") or "",
                    "caption": scene.get("caption", "")[:120],
                    "mermaid_graph": scene_graph,
                    "done": scene.get("node_state", {}).get("done", []),
                    "active": scene.get("node_state", {}).get("active", ""),
                }
                await page.evaluate("window.renderScene(arguments[0])", payload)
                await page.screenshot(path=str(work / f"{frame:05d}.png"))
            await browser.close()

        # captions
        srt = root / "output" / "captions.srt"
        with srt.open("w", encoding="utf-8") as f:
            for i, s in enumerate(scenes, start=1):
                start = (i - 1) * scene_dur
                end = i * scene_dur
                f.write(f"{i}\n{_ts(start)} --> {_ts(end)}\n{s.get('caption','')[:60]}\n\n")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", str(work / "%05d.png"),
            "-vf", f"subtitles={str(srt).replace('\\','/')}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(fps),
            str(output_mp4_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)

    asyncio.run(_run())
    return output_mp4_path

