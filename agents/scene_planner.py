import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from agents.github_reader_agent import get_repo_context
from agents.llm import generate_script as llm_generate_script

logger = logging.getLogger(__name__)

ALLOWED_BEATS = ["problem", "workflow", "ai_insight", "outcome"]
GENERIC_TITLE_BANS = {
    "complex data slow insights",
    "ai powered analysis",
    "better decisions",
    "business growth",
    "talk to data interface",
    "empowered business decisions",
}

DOMAIN_HINTS = [
    "fastapi", "react", "tailwind", "bigquery", "bigquery ml", "vertex ai", "gemini",
    "dashboard", "kpi", "forecast", "root cause", "recommendation", "sales", "conversion",
    "costco", "business center", "nlq", "natural language", "gcp",
]

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "your", "into", "onto", "over",
    "using", "used", "are", "was", "were", "is", "be", "to", "of", "on", "in", "as", "or",
    "an", "a", "at", "by", "it", "its", "their", "they", "we", "our", "you", "can", "will",
    "platform", "solution", "system", "application", "app", "project", "tool", "tools",
}


def _words_limited(text: str, max_words: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return " ".join(cleaned.split()[:max_words])


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _extract_topics(repo_context: Dict[str, Any], product_name: str) -> Dict[str, List[str]]:
    readme = (repo_context.get("readme") or "")[:12000]
    desc = (repo_context.get("description") or "")[:2000]
    features = " ".join(repo_context.get("features") or [])
    tech = " ".join(repo_context.get("tech_stack") or [])
    corpus = f"{product_name} {desc} {features} {tech} {readme}".lower()

    # Keep meaningful bi-grams/trigrams around domain terms.
    tokens = re.findall(r"[a-z0-9\+\-\.]{3,}", corpus)
    tokens = [t for t in tokens if t not in STOPWORDS and not t.isdigit()]
    counts = Counter(tokens)

    # Phrase capture for known architectural/business concepts.
    phrases = []
    phrase_patterns = [
        r"costco business center[s]?",
        r"business center[s]?",
        r"real[- ]time kpi dashboard[s]?",
        r"talk[- ]to[- ]data",
        r"natural language",
        r"bigquery ml",
        r"vertex ai",
        r"root[- ]cause",
        r"sales forecast(?:ing)?",
        r"prescriptive recommendation[s]?",
        r"diagnostic analysis",
        r"dynamic chart generation",
        r"fastapi",
        r"react",
        r"tailwind",
        r"gcp",
    ]
    for pat in phrase_patterns:
        m = re.findall(pat, corpus)
        phrases.extend(sorted(set(m)))

    # Topic groups for the planner prompt.
    data_sources = [p for p in phrases if any(k in p for k in ["pos", "member", "lead", "sales", "kpi", "dashboard", "business center", "costco"])]
    stack = [p for p in phrases if any(k in p for k in ["fastapi", "react", "tailwind", "bigquery", "vertex ai", "gemini", "gcp"])]
    ai_caps = [p for p in phrases if any(k in p for k in ["root", "forecast", "recommend", "diagnostic", "natural language", "talk-to-data"]) ]

    top_terms = [k for k, _ in counts.most_common(25)]
    priority_terms = [t for t in top_terms if t in DOMAIN_HINTS or any(d in t for d in ["costco", "bigquery", "fastapi", "react", "gemini", "forecast", "kpi", "conversion", "dashboard"]) ]

    return {
        "priority_terms": priority_terms[:12],
        "data_sources": data_sources[:8],
        "stack": stack[:8],
        "ai_capabilities": ai_caps[:8],
        "phrases": phrases[:20],
    }


def _sanitize_mermaid(diagram: str, scene_title: str) -> str:
    if not diagram:
        return f"flowchart LR\n  A[Input] --> B[{_words_limited(scene_title, 2) or 'Step'}]\n  B --> C[Outcome]"
    lines = [ln.rstrip() for ln in diagram.splitlines() if ln.strip()]
    if not lines:
        return f"flowchart LR\n  A[Input] --> B[{_words_limited(scene_title, 2) or 'Step'}]\n  B --> C[Outcome]"
    if not lines[0].lower().startswith("flowchart"):
        lines.insert(0, "flowchart LR")

    # Keep only simple node/edge lines and cap nodes for renderer safety.
    clean = [lines[0]]
    node_ids = set()
    for ln in lines[1:]:
        ln = re.sub(r"[^A-Za-z0-9_\-\[\]\(\)\s>.:+\\/]", "", ln)
        if "-->" not in ln:
            continue
        ids = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", ln)
        for i in ids:
            node_ids.add(i)
        clean.append("  " + ln.strip())
        if len(clean) >= 7:
            break

    if len(node_ids) > 6:
        # fallback compact safe shape
        t = _words_limited(scene_title, 2) or "Step"
        return f"flowchart LR\n  A[Input] --> B[{t}]\n  B --> C[Insight]\n  C --> D[Action]"
    if len(clean) < 2:
        t = _words_limited(scene_title, 2) or "Step"
        return f"flowchart LR\n  A[Input] --> B[{t}]\n  B --> C[Outcome]"
    return "\n".join(clean)


def _is_generic_title(title: str) -> bool:
    t = re.sub(r"[^a-z0-9 ]", "", (title or "").lower()).strip()
    return t in GENERIC_TITLE_BANS or any(x == t for x in ["ai insight", "business outcome", "better decisions"]) 


def _normalize_scene(scene: Dict[str, Any], idx: int, required_terms: List[str], product_name: str) -> Dict[str, Any]:
    beat = scene.get("beat")
    if beat not in ALLOWED_BEATS:
        beat = ALLOWED_BEATS[idx - 1]

    title = _words_limited(scene.get("title", f"Scene {idx}"), 4)
    subtitle = _words_limited(scene.get("subtitle", ""), 8)
    caption = _words_limited(scene.get("caption", ""), 10)

    if _is_generic_title(title):
        anchor = _words_limited(required_terms[0] if required_terms else product_name, 2)
        title = _words_limited(f"{anchor} {ALLOWED_BEATS[idx-1]}", 4)

    # Ensure at least one domain anchor in title/subtitle.
    anchor_pool = [t for t in required_terms if len(t) > 2]
    text_blob = f"{title} {subtitle}".lower()
    if anchor_pool and not any(a.lower() in text_blob for a in anchor_pool[:6]):
        subtitle = _words_limited(f"{subtitle} {anchor_pool[0]}".strip(), 8)

    diagram_raw = scene.get("diagram") or scene.get("mermaid_diagram") or ""
    diagram = _sanitize_mermaid(diagram_raw, title)

    return {
        "id": idx,
        "beat": beat,
        "title": title,
        "subtitle": subtitle,
        "caption": caption,
        "mermaid_diagram": diagram,
    }




def _scene_specificity(scene: Dict[str, Any], anchors: List[str]) -> Dict[str, Any]:
    text = f"{scene.get('title','')} {scene.get('subtitle','')} {scene.get('caption','')}".lower()
    matched = [a for a in anchors if a and a.lower() in text]
    generic_penalty = 1 if _is_generic_title(scene.get('title','')) else 0
    mermaid = scene.get('mermaid_diagram','')
    edge_count = mermaid.count('-->')
    score = min(100, max(0, 40 + len(set(matched))*12 + min(edge_count,4)*6 - generic_penalty*25))
    return {"id": scene.get("id"), "score": score, "matched_terms": matched[:6], "edge_count": edge_count, "generic_penalty": generic_penalty}


def _plan_specificity(scenes: List[Dict[str, Any]], anchors: List[str]) -> Dict[str, Any]:
    per_scene = [_scene_specificity(sc, anchors) for sc in scenes]
    overall = int(sum(x['score'] for x in per_scene)/max(1,len(per_scene)))
    return {"specificity_score": overall, "scene_diagnostics": per_scene}

def generate_scene_plan(repo_url: str, product_name: str, architecture_mmd: Optional[str] = None) -> Dict[str, Any]:
    repo_context = get_repo_context(repo_url)
    if not repo_context or "Error" in (repo_context.get("name") or ""):
        raise ValueError("Failed to load repository context for scene planning.")

    readme = (repo_context.get("readme") or "")[:9000]
    desc = (repo_context.get("description") or "")[:1600]
    arch = (architecture_mmd or "")[:4000]
    topics = _extract_topics(repo_context, product_name)

    prompt = f"""
Return ONLY valid JSON with this schema:
{{
  "scenes": [
    {{"id":1,"beat":"problem","title":"","subtitle":"","caption":"","diagram":"flowchart LR\\n  A-->B"}},
    {{"id":2,"beat":"workflow","title":"","subtitle":"","caption":"","diagram":"flowchart LR\\n  A-->B"}},
    {{"id":3,"beat":"ai_insight","title":"","subtitle":"","caption":"","diagram":"flowchart LR\\n  A-->B"}},
    {{"id":4,"beat":"outcome","title":"","subtitle":"","caption":"","diagram":"flowchart LR\\n  A-->B"}}
  ]
}}
Rules:
- Exactly 4 scenes, fixed order: problem, workflow, ai_insight, outcome.
- MUST be repo-specific and demo-ready, not generic marketing copy.
- title <= 4 words, subtitle <= 8 words, caption <= 10 words.
- Avoid generic titles like: Complex Data Slow Insights, AI Powered Analysis, Better Decisions, Business Growth.
- Use these repo-specific anchors where relevant:
  priority_terms={topics['priority_terms']}
  data_sources={topics['data_sources']}
  stack={topics['stack']}
  ai_capabilities={topics['ai_capabilities']}
  phrases={topics['phrases']}
- Mermaid diagram: flowchart only, concise, renderer-safe, <= 6 nodes.
- Include concrete nouns from README and repo description.

Product: {product_name}
Description: {desc}
README excerpt: {readme}
Architecture Mermaid (optional): {arch}
"""

    raw = llm_generate_script(prompt)
    raw = (raw or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(raw)
    except Exception as e:
        logger.warning("Scene plan JSON parse failed: %s", e)
        raise ValueError("Scene plan generation returned invalid JSON.") from e

    scenes = parsed.get("scenes") if isinstance(parsed, dict) else parsed
    if not isinstance(scenes, list) or len(scenes) < 4:
        raise ValueError("Scene plan generation did not return 4 scenes.")

    required_terms = topics["priority_terms"] or topics["phrases"] or [product_name]
    normalized = [_normalize_scene(scenes[i], i + 1, required_terms, product_name) for i in range(4)]

    # Final guard: reject still-generic outputs.
    for sc in normalized:
        if _is_generic_title(sc["title"]):
            raise ValueError("Scene plan remained too generic after normalization.")

    quality = _plan_specificity(normalized, required_terms)
    return {
        "repo_url": repo_url,
        "product_name": product_name,
        "topics": topics,
        "scenes": normalized,
        "repo_context": repo_context,
        **quality,
    }
