from typing import Any, Dict, List
import requests

from agents.shared_github import parse_owner_repo, gh_get


def competitive_analyzer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    repo_url = state['repo_url']
    token = state['github_token']
    _, repo_name = parse_owner_repo(repo_url)

    q = f'{repo_name} git automation in:name,description'
    data = gh_get(f'https://api.github.com/search/repositories?q={requests.utils.quote(q)}&sort=stars&order=desc&per_page=5', token)
    items = data.get('items', [])
    competitors: List[Dict[str, Any]] = []
    for it in items[:3]:
        competitors.append({
            'name': it.get('full_name'),
            'url': it.get('html_url'),
            'stars': it.get('stargazers_count', 0),
            'updated_at': it.get('updated_at'),
            'comparison': it.get('description') or '',
        })

    state['competitors'] = {
        'competitors': competitors,
        'unique_selling_points': [
            'Single-repo focused README pipeline',
            'Structured profile -> deterministic markdown output',
            'Integrated publish-to-branch flow',
        ],
    }
    state['progress'].append({'stage': 'competitive_analyzer', 'percent': 70, 'message': 'Competitive analysis complete'})
    return state
