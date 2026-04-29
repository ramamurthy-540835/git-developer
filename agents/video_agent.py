import os
import math
import re
import json
import logging
from agents.llm import generate_script as llm_generate_script
from agents.planner_agent import build_scene_plan
from agents.remotion_renderer import render_with_remotion
from agents.local_renderer import render_mermaid_video

logging.basicConfig(level=logging.INFO)

def _clean_text(value: str) -> str:
    value = (value or "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    return re.sub(r"\s+", " ", value).strip()

def _split_sentences(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]

def _to_words(text: str, limit: int) -> str:
    return " ".join(_clean_text(text).split()[:limit]).strip()

def _theme_for_repo(title: str) -> dict:
    lower = (title or "").lower()
    if "health" in lower or "care" in lower:
        return {"bg": "0x0F1A14", "accent": "0x88E0A3", "text": "0xE8FFF1", "bar": "0x173325"}
    if "meter" in lower or "energy" in lower:
        return {"bg": "0x161A24", "accent": "0x8EC5FF", "text": "0xECF5FF", "bar": "0x24324A"}
    if "finance" in lower or "cost" in lower:
        return {"bg": "0x1A1510", "accent": "0xFFD38A", "text": "0xFFF7E8", "bar": "0x3A2A1A"}
    return {"bg": "0x101820", "accent": "0xBBD4FF", "text": "0xECF3FF", "bar": "0x1F2A3A"}

def _extract_mermaid_steps(repo_context: dict | None) -> list[str]:
    readme = _clean_text((repo_context or {}).get("readme") or "")
    if "flowchart" not in readme.lower():
        return []
    # Heuristic extraction of arrow flow labels from mermaid-like content in README preview.
    raw = (repo_context or {}).get("readme") or ""
    lines = [l.strip() for l in raw.splitlines() if "-->" in l]
    steps = []
    for line in lines[:8]:
        txt = re.sub(r"[^A-Za-z0-9 \-\>\[\]\(\)_:/]", " ", line)
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            steps.append(txt)
    return steps

def _fallback_scene_plan(title: str, transcript: str, repo_context: dict | None) -> list[dict]:
    desc = _clean_text((repo_context or {}).get("description") or "")
    readme = _clean_text((repo_context or {}).get("readme") or "")
    tech = ", ".join((repo_context or {}).get("tech_stack") or [])
    text = _clean_text(" ".join([title, desc, readme, transcript]))
    meter_mode = "meter" in text.lower() or "ocr" in text.lower() or "camera" in text.lower()
    if meter_mode:
        return [
            {"title":"Product Value","subtitle":"Automated meter reading platform","voiceover":"Electricity Meter Reader Pro Expo automates utility data capture with a mobile-first workflow.", "visual_points":["Mobile field workflow","Faster collection cycles","Higher reading accuracy"]},
            {"title":"Business Problem","subtitle":"Manual reading causes errors","voiceover":"Manual meter entry is slow, inconsistent, and expensive for utility operations and billing teams.", "visual_points":["Human transcription errors","Delayed billing cycles","Higher field costs"]},
            {"title":"Capture Workflow","subtitle":"Camera-driven meter capture","voiceover":"Field staff capture meter images directly in app, reducing manual steps and improving consistency.", "visual_points":["In-app camera capture","Guided meter framing","Immediate upload"]},
            {"title":"AI Extraction","subtitle":"OCR extracts reading values","voiceover":"AI OCR processes each image, extracts meter values, and returns structured data for downstream validation.", "visual_points":["OCR inference layer","Structured value output","Low manual intervention"]},
            {"title":"Validation Layer","subtitle":"Confirm and store results","voiceover":"The platform validates extracted readings and stores approved records for reporting and billing.", "visual_points":["Validation checkpoints","Audit-friendly records","Reliable data quality"]},
            {"title":"Architecture","subtitle":"Mobile, API, cloud storage","voiceover":"Core components include mobile capture, backend processing APIs, and scalable cloud data services.", "visual_points":["Mobile client","Backend API services", tech or "Cloud storage layer"]},
            {"title":"Operational Output","subtitle":"Near real-time insight delivery","voiceover":"Teams receive usable meter data quickly, improving planning, billing velocity, and operational visibility.", "visual_points":["Faster billing cycles","Actionable field insights","Better planning inputs"]},
            {"title":"Business Value","subtitle":"Scalable utility automation","voiceover":"This solution reduces operational cost and enables reliable, scalable meter-data workflows across regions.", "visual_points":["Lower operating cost","Scalable deployment","Consistent data pipeline"]},
        ]
    # Generic fallback
    return [
        {"title":"Product Value","subtitle":"Enterprise workflow acceleration","voiceover":_to_words(f"{title} helps teams automate core workflows and improve operational outcomes.", 28), "visual_points":["Workflow automation","Operational consistency","Business impact"]},
        {"title":"Business Problem","subtitle":"Manual work limits scale","voiceover":"Legacy manual steps create delays, inconsistencies, and cost overhead across delivery teams.", "visual_points":["Slow handoffs","Inconsistent outputs","Higher costs"]},
        {"title":"Core Workflow","subtitle":"Structured request to result","voiceover":"Users submit requests, backend services process them, and outputs are generated through a repeatable pipeline.", "visual_points":["Request intake","Processing pipeline","Result delivery"]},
        {"title":"Key Capabilities","subtitle":"Production-ready platform features","voiceover":"The platform combines configurable inputs, automated processing, and integration-ready outputs.", "visual_points":["Configurable inputs","Automated processing","Integration outputs"]},
        {"title":"Architecture","subtitle":"Composable service components","voiceover":"Architecture separates interface, processing, and storage layers for maintainability and scale.", "visual_points":["Interface layer","Processing layer","Storage layer"]},
        {"title":"Automation Layer","subtitle":"AI-assisted decision support","voiceover":"Automation components enrich outputs and reduce repetitive effort in high-volume operations.", "visual_points":["Assisted decisions","Reduced manual effort","Higher throughput"]},
        {"title":"Outputs","subtitle":"Actionable delivery artifacts","voiceover":"Teams receive structured outputs for operational use, analysis, and downstream execution.", "visual_points":["Structured artifacts","Operational visibility","Downstream readiness"]},
        {"title":"Business Value","subtitle":"Scalable enterprise impact","voiceover":"Overall, the solution improves speed, quality, and cost performance at enterprise scale.", "visual_points":["Speed improvements","Quality uplift","Cost control"]},
    ]

def _validate_scene(scene: dict) -> bool:
    if not isinstance(scene, dict):
        return False
    title = _to_words(scene.get("title", ""), 5)
    subtitle = _to_words(scene.get("subtitle", ""), 12)
    voiceover = _to_words(scene.get("voiceover", ""), 28)
    points = scene.get("visual_points", [])
    if not title or not subtitle or not voiceover or not isinstance(points, list):
        return False
    if len(points) < 3:
        return False
    return True

def _build_story_plan_with_gemini(title: str, transcript: str, repo_context: dict | None) -> list[dict]:
    context_blob = json.dumps(repo_context or {}, ensure_ascii=False)[:20000]
    prompt = f"""
Return ONLY valid JSON.
Create a HIGH-QUALITY YouTube-style product demo video plan.
This is NOT documentation.
This is a cinematic, engaging product demo.
Duration: 60-90 seconds.
Schema:
[
  {{
    "title": "Short scene title",
    "subtitle": "Short hook or statement",
    "voiceover": "Natural spoken narration (engaging, human tone)",
    "visual_points": ["short point", "short point", "short point"],
    "style": "hook | problem | demo | ai | architecture | impact | closing"
  }}
]
Rules:
- 6 to 8 scenes ONLY
- Title max 5 words
- Subtitle max 10 words
- Voiceover max 24 words
- 3 visual points max, each <= 6 words
- NO repetition across scenes
- MUST feel like a product demo video (not documentation)
- Use action words: capture, analyze, process, deliver
- Avoid generic words like system, solution, platform
- Scenes must include real domain terms if present in context:
  meter reading, OCR, camera capture, validation, billing
- no hallucinated cloud services unless present in repo context
- output strict JSON only

Story flow MUST be:
1. Hook
2. Problem
3. Product intro
4. Core workflow demo
5. AI/automation highlight
6. Architecture (simple)
7. Business impact
8. Closing punch

Tone:
- confident
- modern
- product-focused
- slightly marketing style

Transcript:
{transcript}
Repo context:
{context_blob}
"""
    try:
        raw = _clean_text(llm_generate_script(prompt))[:30000]
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        scenes = parsed if isinstance(parsed, list) else parsed.get("scenes", [])
        cleaned = []
        for s in scenes:
            if not _validate_scene(s):
                continue
            cleaned.append({
                "title": _to_words(s.get("title", ""), 5),
                "subtitle": _to_words(s.get("subtitle", ""), 10),
                "voiceover": _to_words(s.get("voiceover", ""), 24),
                "visual_points": [_to_words(p, 6) for p in s.get("visual_points", [])[:3]],
            })
        if 6 <= len(cleaned) <= 8:
            return cleaned
    except Exception as e:
        logging.warning(f"Gemini scene plan generation failed, using heuristic fallback: {e}")
    return _fallback_scene_plan(title, transcript, repo_context)

def mp3_to_video(mp3_path: str, output_name: str, title: str, transcript: str, repo_context: dict | None = None) -> str:
    """
    Convert MP3 narration into MP4 video using FFmpeg.

    Creates a simple video with a black background and audio from the MP3.
    Output format: MP4. Saves under the 'output/' directory.

    Args:
        mp3_path (str): Path to the input MP3 file.
        output_name (str): Desired name for the output MP4 file (e.g., "video.mp4").

    Returns:
        str: Path to the created MP4 file.
    """
    try:
        import ffmpeg
    except ModuleNotFoundError as e:
        raise RuntimeError("Missing dependency 'ffmpeg-python'. Run: pip install ffmpeg-python") from e

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_mp4_path = os.path.join(output_dir, output_name)

    # Get audio duration to set video duration
    probe = ffmpeg.probe(mp3_path)
    duration = float(probe['streams'][0]['duration'])

    # Try Remotion first for higher-quality deterministic scene rendering.
    output_dir = "output"
    output_mp4_path = os.path.join(output_dir, output_name)
    try:
        plan = build_scene_plan(title, transcript, duration_seconds=32, fps=30)
        # Primary local path: Mermaid-led Playwright renderer
        try:
            return render_mermaid_video(plan, title, output_mp4_path, fps=30)
        except Exception as e1:
            logging.warning("Playwright Mermaid renderer failed, trying Remotion fallback: %s", e1)
        return render_with_remotion(plan, title, output_mp4_path)
    except Exception as e:
        logging.warning("Remotion path unavailable, falling back to ffmpeg overlay renderer: %s", e)

    # Build storyboard text for fallback overlay progression.
    scenes = _build_story_plan_with_gemini(title, transcript, repo_context)
    mermaid_steps = _extract_mermaid_steps(repo_context)
    theme = _theme_for_repo(title)

    # Render settings for better perceived quality and smoother output.
    width = 1920
    height = 1080
    fps = 30
    video_input = ffmpeg.input(f'color=c={theme["bg"]}:s={width}x{height}:r={fps}:d={duration}', f='lavfi')
    # Top brand bar
    draw_chain = video_input.drawbox(x=0, y=0, width=width, height=110, color=theme["bar"], t='fill')

    # Title and dynamic flow text overlays.
    draw_chain = draw_chain.drawtext(
        text=_clean_text(title) or "Product Demo",
        fontcolor=theme["text"],
        fontsize=42,
        x=48,
        y=35
    )

    segment = max(6.5, duration / max(1, len(scenes)))
    subtitle_lines = []
    for idx, scene in enumerate(scenes):
        start = idx * segment
        end = min(duration, (idx + 1) * segment)
        safe_title = _clean_text(scene["title"]).replace(":", "\\:").replace("'", "\\'")
        safe_subtitle = _clean_text(scene["subtitle"]).replace(":", "\\:").replace("'", "\\'")
        safe_voice = _clean_text(scene["voiceover"]).replace(":", "\\:").replace("'", "\\'")
        p1 = _clean_text(scene["visual_points"][0]).replace(":", "\\:").replace("'", "\\'")
        p2 = _clean_text(scene["visual_points"][1]).replace(":", "\\:").replace("'", "\\'")
        p3 = _clean_text(scene["visual_points"][2]).replace(":", "\\:").replace("'", "\\'")
        progress_width = int(width * ((idx + 1) / len(scenes)))
        draw_chain = draw_chain.drawbox(
            x=0, y=height - 14, width=progress_width, height=14, color=theme["accent"], t='fill',
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawtext(
            text=f"Scene {idx + 1} / {len(scenes)}",
            fontcolor=theme["accent"],
            fontsize=28,
            x=width-320,
            y=38,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawtext(
            text=safe_title,
            fontcolor=theme["accent"],
            fontsize=52,
            x=90,
            y=180,
            box=1,
            boxcolor='0x00000088',
            boxborderw=12,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawtext(
            text=safe_subtitle,
            fontcolor=theme["text"],
            fontsize=34,
            x=90,
            y=260,
            box=1,
            boxcolor='0x00000066',
            boxborderw=10,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawbox(
            x=980, y=180, width=840, height=430, color='0x00000088', t='fill',
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        # Mermaid-style / business-flow mini diagram band.
        draw_chain = draw_chain.drawbox(
            x=90, y=760, width=1730, height=180, color='0x00000066', t='fill',
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        if mermaid_steps:
            flow_text = _clean_text(mermaid_steps[min(idx, len(mermaid_steps)-1)]).replace(":", "\\:").replace("'", "\\'")
        else:
            flow_text = f"Business Flow: Capture -> Analyze -> Validate -> Deliver"
        draw_chain = draw_chain.drawtext(
            text=flow_text,
            fontcolor=theme["accent"],
            fontsize=30,
            x=120,
            y=825,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawtext(
            text=f"- {p1}",
            fontcolor=theme["text"],
            fontsize=34,
            x=1030,
            y=260,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        # Thin animation: gentle left-right drift on bullets by scene.
        drift_x = 1030 + (idx % 2) * 12
        draw_chain = draw_chain.drawtext(
            text=f"- {p2}",
            fontcolor=theme["text"],
            fontsize=34,
            x=drift_x,
            y=340,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        draw_chain = draw_chain.drawtext(
            text=f"- {p3}",
            fontcolor=theme["text"],
            fontsize=34,
            x=drift_x,
            y=420,
            enable=f"between(t,{start:.2f},{end:.2f})"
        )
        subtitle_lines.append((start, end, safe_voice))

    # Burn captions via ASS-like subtitles filter by generating an SRT file.
    srt_path = output_mp4_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (start, end, text_line) in enumerate(subtitle_lines, start=1):
            def ts(v: float) -> str:
                ms = int((v - int(v)) * 1000)
                s = int(v) % 60
                m = (int(v) // 60) % 60
                h = int(v) // 3600
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            f.write(f"{i}\n{ts(start)} --> {ts(end)}\n{text_line}\n\n")
    draw_chain = draw_chain.filter("subtitles", srt_path.replace("\\", "/"))
    # Subtle cinematic motion and fades.
    draw_chain = draw_chain.filter("zoompan", z="min(zoom+0.0006,1.06)", d=1, s="1920x1080", fps=30)
    draw_chain = draw_chain.filter("fade", type="in", start_time=0, duration=0.6)
    draw_chain = draw_chain.filter("fade", type="out", start_time=max(0, duration-0.6), duration=0.6)
    
    # Input audio stream
    audio_input = ffmpeg.input(mp3_path)

    # Merge video and audio streams
    # -c:v libx264: encode video with h.264
    # -c:a aac: encode audio with aac
    # -pix_fmt yuv420p: pixel format, often required for wider compatibility
    (
        ffmpeg
        .output(
            draw_chain,
            audio_input,
            output_mp4_path,
            vcodec='libx264',
            acodec='aac',
            pix_fmt='yuv420p',
            r=fps,
            video_bitrate='4500k',
            audio_bitrate='192k',
            crf=18,
            preset='slow',
            movflags='+faststart',
            shortest=None
        )
        .run(overwrite_output=True)
    )

    try:
        os.remove(srt_path)
    except Exception:
        pass
    return output_mp4_path
