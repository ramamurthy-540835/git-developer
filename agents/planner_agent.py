import json
import logging
import re
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ValidationError, field_validator

from agents.llm import generate_script as llm_generate_script

logging.basicConfig(level=logging.INFO)


def _clean_text(value: str) -> str:
    value = (value or "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    return re.sub(r"\s+", " ", value).strip()


def _limit_words(text: str, n: int) -> str:
    return " ".join(_clean_text(text).split()[:n]).strip()


class SceneSpec(BaseModel):
    id: int
    beat: Literal["problem", "workflow", "ai_insight", "outcome"]
    header: str
    caption: str
    active_node: str
    node_state: Dict[str, Any]
    active_subgraph: str = ""
    dimmed_subgraphs: List[str] = []
    camera_hint: Literal["zoom_to_node", "static", "drift_left", "drift_right"] = "static"

    @field_validator("header")
    @classmethod
    def header_limit(cls, v: str) -> str:
        return _limit_words(v, 3)

    @field_validator("caption")
    @classmethod
    def caption_limit(cls, v: str) -> str:
        cleaned = _clean_text(v)
        if len(cleaned) > 60:
            cleaned = cleaned[:60]
        return _limit_words(cleaned, 10)


class VideoSpec(BaseModel):
    duration_s: int
    fps: int
    resolution: Literal["1080p", "720p"]
    aspect: Literal["16:9"]


class ScenePlan(BaseModel):
    video: VideoSpec
    mermaid_graph: str
    scenes: List[SceneSpec]


def _fallback_plan(product_name: str, duration_seconds: int) -> Dict[str, Any]:
    scenes = [
        {
            "id": 1,
            "beat": "problem",
            "header": "Data challenge",
            "caption": "Reports take days, decisions slip.",
            "active_node": "Slow report",
            "active_subgraph": "UI",
            "dimmed_subgraphs": ["API", "AI", "Data"],
            "node_state": {"done": ["Raw data"], "active": "Slow report", "pending": ["AI insight", "Action"]},
            "camera_hint": "zoom_to_node",
        },
        {
            "id": 2,
            "beat": "workflow",
            "header": "Real-time view",
            "caption": "Live KPIs across every center.",
            "active_node": "Raw data",
            "active_subgraph": "API",
            "dimmed_subgraphs": ["UI", "AI", "Data"],
            "node_state": {"done": [], "active": "Raw data", "pending": ["Slow report", "AI insight", "Action"]},
            "camera_hint": "drift_right",
        },
        {
            "id": 3,
            "beat": "ai_insight",
            "header": "Talk to data",
            "caption": "Ask in plain English. Get answers.",
            "active_node": "AI insight",
            "active_subgraph": "AI",
            "dimmed_subgraphs": ["UI", "API", "Data"],
            "node_state": {"done": ["Raw data", "Slow report"], "active": "AI insight", "pending": ["Action"]},
            "camera_hint": "zoom_to_node",
        },
        {
            "id": 4,
            "beat": "outcome",
            "header": "Better decisions",
            "caption": "From data to action, instantly.",
            "active_node": "Action",
            "active_subgraph": "Data",
            "dimmed_subgraphs": ["UI", "API", "AI"],
            "node_state": {"done": ["Raw data", "Slow report", "AI insight"], "active": "Action", "pending": []},
            "camera_hint": "static",
        },
    ]
    return {
        "video": {"duration_s": duration_seconds, "fps": 30, "resolution": "1080p", "aspect": "16:9"},
        "mermaid_graph": "flowchart LR\n  Raw data --> Slow report --> AI insight --> Action",
        "scenes": scenes,
    }


def build_scene_plan(product_name: str, narration_text: str, duration_seconds: int = 32, fps: int = 30) -> Dict[str, Any]:
    duration_seconds = max(8, min(60, int(duration_seconds)))
    input_text = _clean_text(narration_text)[:12000]
    prompt = f"""
You are a Demo Video Director. Convert the user's brief into a strict
Scene Plan JSON for a {duration_seconds}-second product demo at {fps} fps.

INPUT
- product: {product_name}
- narration: {input_text}
- style: modern enterprise SaaS, smooth camera, clean composition

RULES
1. Always produce exactly 4 scenes. Each scene is exactly {duration_seconds/4:.1f}s.
2. Each scene maps to one of: problem, workflow, ai_insight, outcome.
3. Per scene, return:
   - id (1-4)
   - beat (problem | workflow | ai_insight | outcome)
   - header         : <= 3 words
   - caption        : ONE sentence, <= 10 words, <= 60 chars
   - active_node    : node id/name from graph
   - node_state     : {{done:[], active:'', pending:[]}}
   - active_subgraph and dimmed_subgraphs (optional)
   - camera_hint    : zoom_to_node | static | drift_left | drift_right
4. Never output stage directions like "user screen", "shows", "display".
5. Across 4 scenes, active progression should move through graph.
6. Output ONLY valid JSON. No prose, no markdown fences.

Output shape:
{{
  "video": {{ "duration_s": {duration_seconds}, "fps": {fps}, "resolution": "1080p", "aspect": "16:9" }},
  "mermaid_graph": "flowchart ...",
  "scenes": [ ... ]
}}
"""
    try:
        raw = llm_generate_script(prompt).strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        validated = ScenePlan.model_validate(parsed)
        if len(validated.scenes) != 4:
            raise ValueError("scene count must be exactly 4")
        for i, s in enumerate(validated.scenes):
            if s.id != i + 1:
                raise ValueError("scene id progression invalid")
        return validated.model_dump()
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        logging.warning("Planner validation failed, using fallback: %s", e)
        return _fallback_plan(product_name, duration_seconds)
    except Exception as e:
        logging.warning("Planner generation failed, using fallback: %s", e)
        return _fallback_plan(product_name, duration_seconds)
