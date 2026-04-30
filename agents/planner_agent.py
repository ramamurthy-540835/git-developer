import json
import logging
import re
import base64
from typing import Any, Dict, List, Literal, Optional

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
    beat: Literal["problem", "workflow", "ai_insight", "outcome", "architecture"]
    header: str
    caption: str
    active_node: str
    node_state: Dict[str, Any]
    active_subgraph: str = ""
    dimmed_subgraphs: List[str] = []
    camera_hint: Literal["zoom_to_node", "static", "drift_left", "drift_right"] = "static"
    sceneType: Literal["text", "diagram"] = "text"
    mermaidDiagramUrl: Optional[str] = None

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


def _fallback_plan(product_name: str, duration_seconds: int, repo_context: Dict[str, Any]) -> Dict[str, Any]:
    mermaid_diagram_url = repo_context.get("mermaid_diagram_url")
    
    base_scenes = [
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
            "sceneType": "text",
            "mermaidDiagramUrl": None,
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
            "sceneType": "text",
            "mermaidDiagramUrl": None,
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
            "sceneType": "text",
            "mermaidDiagramUrl": None,
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
            "sceneType": "text",
            "mermaidDiagramUrl": None,
        },
    ]

    all_scenes: List[Dict[str, Any]] = []

    if mermaid_diagram_url:
        diagram_scene = {
            "id": 0, # Temporarily 0, will re-index later
            "beat": "architecture",
            "header": "Architecture",
            "caption": "System overview and data flow",
            "active_node": "", # No active node for diagram
            "node_state": {},
            "active_subgraph": "",
            "dimmed_subgraphs": [],
            "camera_hint": "static",
            "sceneType": "diagram",
            "mermaidDiagramUrl": mermaid_diagram_url,
        }
        # Insert diagram scene after the 'workflow' beat (index 1 in 0-indexed base_scenes)
        all_scenes.extend(base_scenes[:2]) # problem, workflow
        all_scenes.append(diagram_scene)   # architecture
        all_scenes.extend(base_scenes[2:]) # ai_insight, outcome
    else:
        all_scenes = base_scenes[:]

    # Re-index IDs for all scenes
    for i, scene in enumerate(all_scenes):
        scene["id"] = i + 1

    final_duration_s = duration_seconds

    return {
        "video": {"duration_s": final_duration_s, "fps": 30, "resolution": "1080p", "aspect": "16:9"},
        "mermaid_graph": "flowchart LR\n  Raw data --> Slow report --> AI insight --> Action", # This should ideally come from the LLM or be constructed. For fallback, it's static.
        "scenes": all_scenes,
    }


def build_scene_plan(product_name: str, narration_text: str, repo_context: Dict[str, Any], duration_seconds: int = 32, fps: int = 30) -> Dict[str, Any]:
    duration_seconds = max(8, min(60, int(duration_seconds)))
    input_text = _clean_text(narration_text)[:12000]

    mermaid_diagram_url = repo_context.get("mermaid_diagram_url")
    
    num_llm_scenes = 4
    total_final_scenes = num_llm_scenes
    diagram_scene_spec: Optional[Dict[str, Any]] = None

    if mermaid_diagram_url:
        total_final_scenes = 5
        diagram_scene_spec = {
            "id": 0, # Placeholder
            "beat": "architecture",
            "header": "Architecture",
            "caption": "System overview and data flow",
            "active_node": "",
            "node_state": {},
            "active_subgraph": "",
            "dimmed_subgraphs": [],
            "camera_hint": "static",
            "sceneType": "diagram",
            "mermaidDiagramUrl": mermaid_diagram_url,
        }

    # Calculate duration per scene for the *total* number of final scenes
    duration_per_scene = duration_seconds / total_final_scenes

    # The LLM will always produce 4 scenes (problem, workflow, ai_insight, outcome)
    # We will insert the diagram scene manually after validation.
    prompt = f"""
You are a Demo Video Director. Convert the user's brief into a strict
Scene Plan JSON for a {duration_seconds}-second product demo at {fps} fps.

INPUT
- product: {product_name}
- narration: {input_text}
- style: modern enterprise SaaS, smooth camera, clean composition

RULES
1. Always produce exactly {num_llm_scenes} scenes. Each scene is approximately {duration_per_scene:.1f}s.
2. Each scene maps to one of: problem | workflow | ai_insight | outcome.
3. Per scene, return:
   - id (1-{num_llm_scenes})
   - beat (problem | workflow | ai_insight | outcome)
   - header         : <= 3 words
   - caption        : ONE sentence, <= 10 words, <= 60 chars
   - active_node    : node id/name from graph
   - node_state     : {{"done": [], "active": "", "pending": []}}
   - active_subgraph and dimmed_subgraphs (optional)
   - camera_hint    : zoom_to_node | static | drift_left | drift_right
   - sceneType      : "text" (always for LLM generated scenes)
   - mermaidDiagramUrl: null (always for LLM generated scenes)
4. Never output stage directions like "user screen", "shows", "display".
5. Across {num_llm_scenes} scenes, active progression should move through graph.
6. Output ONLY valid JSON. No prose, no markdown fences.

Output shape:
{{
  "video": {{ "duration_s": {duration_seconds}, "fps": {fps}, "resolution": "1080p", "aspect": "16:9" }},
  "mermaid_graph": "flowchart ...",
  "scenes": [
    {{
      "id": 1,
      "beat": "problem",
      "header": "...",
      "caption": "...",
      "active_node": "...",
      "node_state": {{"done": [], "active": "", "pending": []}},
      "active_subgraph": "",
      "dimmed_subgraphs": [],
      "camera_hint": "static",
      "sceneType": "text",
      "mermaidDiagramUrl": null
    }},
    // ... {num_llm_scenes} scenes
  ]
}}
