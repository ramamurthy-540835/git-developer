import base64
import os
import re
from typing import Any, Dict, List

import requests


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    m = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not m:
        raise ValueError(f'Invalid GitHub URL: {repo_url}')
    return m.group(1), m.group(2).replace('.git', '')


def _headers(github_token: str | None = None) -> Dict[str, str]:
    token = github_token or os.getenv('GITHUB_TOKEN', '')
    if not token:
        raise RuntimeError('Missing GitHub token')
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
    }


def gh_get(url: str, github_token: str) -> Any:
    r = requests.get(url, headers=_headers(github_token), timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_user(github_token: str) -> Dict[str, Any]:
    return gh_get('https://api.github.com/user', github_token)


def list_repos(github_token: str, per_page: int = 50) -> List[Dict[str, Any]]:
    data = gh_get(f'https://api.github.com/user/repos?per_page={per_page}&sort=updated', github_token)
    repos = []
    for r in data:
        repos.append({
            'name': r.get('name'),
            'full_name': r.get('full_name'),
            'url': r.get('html_url'),
            'description': r.get('description') or '',
            'stars': r.get('stargazers_count', 0),
        })
    return repos


def fetch_repo_metadata(owner: str, repo: str, github_token: str) -> Dict[str, Any]:
    meta = gh_get(f'https://api.github.com/repos/{owner}/{repo}', github_token)
    return {
        'name': meta.get('name'),
        'full_name': meta.get('full_name'),
        'repo_url': meta.get('html_url'),
        'description': meta.get('description') or '',
        'primary_language': meta.get('language') or '',
        'topics': meta.get('topics') or [],
        'default_branch': meta.get('default_branch') or 'main',
        'stars': meta.get('stargazers_count', 0),
        'forks': meta.get('forks_count', 0),
        'updated_at': meta.get('updated_at'),
    }


def fetch_tree(owner: str, repo: str, branch: str, github_token: str) -> List[str]:
    tree = gh_get(f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1', github_token)
    return [n.get('path') for n in tree.get('tree', []) if n.get('type') == 'blob' and n.get('path')]


def fetch_file(owner: str, repo: str, path: str, github_token: str) -> str:
    url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    r = requests.get(url, headers=_headers(github_token), timeout=30)
    if r.status_code != 200:
        return ''
    payload = r.json()
    content = payload.get('content')
    if not content:
        return ''
    try:
        return base64.b64decode(content).decode('utf-8', errors='replace')
    except Exception:
        return ''


def publish_readme(repo_url: str, readme_content: str, branch: str, commit_message: str, github_token: str) -> Dict[str, Any]:
    owner, repo = parse_owner_repo(repo_url)
    headers = _headers(github_token)
    get_url = f'https://api.github.com/repos/{owner}/{repo}/contents/README.md?ref={branch}'
    get_resp = requests.get(get_url, headers=headers, timeout=30)
    sha = get_resp.json().get('sha') if get_resp.status_code == 200 else None

    payload = {
        'message': commit_message,
        'content': base64.b64encode(readme_content.encode('utf-8')).decode('utf-8'),
        'branch': branch,
    }
    if sha:
        payload['sha'] = sha

    put_url = f'https://api.github.com/repos/{owner}/{repo}/contents/README.md'
    put_resp = requests.put(put_url, headers=headers, json=payload, timeout=30)
    if put_resp.status_code not in (200, 201):
        raise RuntimeError(f'Publish failed: {put_resp.status_code} {put_resp.text}')
    return {'success': True, 'repo': f'{owner}/{repo}', 'branch': branch}
