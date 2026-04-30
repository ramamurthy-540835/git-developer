from typing import Any, Dict, List, TypedDict

from agents.repo_analyzer import repo_analyzer_agent
from agents.competitive_analyzer import competitive_analyzer_agent
from agents.best_practices_advisor import best_practices_advisor_agent
from agents.readme_composer import (
    readme_composer_agent,
    validate_and_repair_readme_agent,
    extract_topical_insights_agent,
    quality_gate_agent,
)

try:
    from langgraph.graph import StateGraph, START, END
except Exception:
    StateGraph = None
    START = 'START'
    END = 'END'


class RepoState(TypedDict, total=False):
    repo_url: str
    github_token: str
    repo_profile: Dict[str, Any]
    competitors: Dict[str, Any]
    best_practices: Dict[str, Any]
    readme_markdown: str
    metrics: Dict[str, Any]
    progress: List[Dict[str, Any]]
    errors: List[str]


def _safe(node_fn, state: RepoState, name: str) -> RepoState:
    try:
        return node_fn(state)
    except Exception as e:
        state.setdefault('errors', []).append(f'{name}: {e}')
        state.setdefault('progress', []).append({'stage': name, 'percent': state.get('progress', [{}])[-1].get('percent', 0) if state.get('progress') else 0, 'message': f'{name} failed; continuing with fallback'})
        return state


def _invoke_fallback(initial: RepoState) -> RepoState:
    state = dict(initial)
    state.setdefault('progress', [])
    state = _safe(repo_analyzer_agent, state, 'repo_analyzer')
    state = _safe(competitive_analyzer_agent, state, 'competitive_analyzer')
    state = _safe(best_practices_advisor_agent, state, 'best_practices')
    state = _safe(extract_topical_insights_agent, state, 'topical_insights')
    state = _safe(readme_composer_agent, state, 'readme_composer')
    state = _safe(quality_gate_agent, state, 'quality_gate')
    if not (state.get('metrics') or {}).get('quality_gate_passed', True):
        state = _safe(readme_composer_agent, state, 'readme_composer_retry')
        state = _safe(quality_gate_agent, state, 'quality_gate_retry')
    state = _safe(validate_and_repair_readme_agent, state, 'readme_qc')
    return state


def build_readme_workflow():
    if StateGraph is None:
        return None
    graph = StateGraph(RepoState)
    graph.add_node('analyze_repo', repo_analyzer_agent)
    graph.add_node('competitive_analysis', competitive_analyzer_agent)
    graph.add_node('best_practices', best_practices_advisor_agent)
    graph.add_node('topical_insights', extract_topical_insights_agent)
    graph.add_node('compose_readme', readme_composer_agent)
    graph.add_node('quality_gate', quality_gate_agent)
    graph.add_node('readme_qc', validate_and_repair_readme_agent)

    graph.add_edge(START, 'analyze_repo')
    graph.add_edge('analyze_repo', 'competitive_analysis')
    graph.add_edge('analyze_repo', 'best_practices')
    graph.add_edge('competitive_analysis', 'topical_insights')
    graph.add_edge('best_practices', 'topical_insights')
    graph.add_edge('topical_insights', 'compose_readme')
    graph.add_edge('compose_readme', 'quality_gate')
    graph.add_edge('quality_gate', 'readme_qc')
    graph.add_edge('readme_qc', END)
    return graph.compile()


def run_workflow(initial: RepoState) -> RepoState:
    workflow = build_readme_workflow()
    if workflow is None:
        return _invoke_fallback(initial)
    try:
        return workflow.invoke(initial)
    except Exception:
        return _invoke_fallback(initial)
