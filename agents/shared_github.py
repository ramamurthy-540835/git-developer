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
            'id': r.get('id'),
            'name': r.get('name'),
            'full_name': r.get('full_name'),
            'url': r.get('html_url'),
            'description': r.get('description') or '',
            'stargazers_count': r.get('stargazers_count', 0),
            'language': r.get('language') or '',
        })
    return repos


def fetch_repo_metadata(owner: str, repo: str, github_token: str) -> Dict[str, Any]:
    data = gh_get(f'https://api.github.com/repos/{owner}/{repo}', github_token)
    return {
        'name': data.get('name') or repo,
        'full_name': data.get('full_name', f'{owner}/{repo}'),
        'description': data.get('description') or '',
        'default_branch': data.get('default_branch', 'main'),
        'language': data.get('language') or '',
        'stars': data.get('stargazers_count', 0),
        'forks': data.get('forks_count', 0),
        'open_issues': data.get('open_issues_count', 0),
    }


def fetch_tree(owner: str, repo: str, branch: str, github_token: str) -> List[str]:
    data = gh_get(
        f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1',
        github_token,
    )
    return [item.get('path', '') for item in data.get('tree', []) if item.get('type') == 'blob']


def fetch_file(owner: str, repo: str, path: str, github_token: str) -> str:
    data = gh_get(f'https://api.github.com/repos/{owner}/{repo}/contents/{path}', github_token)
    if data.get('encoding') == 'base64' and data.get('content'):
        return base64.b64decode(data['content']).decode('utf-8', errors='replace')
    return ''


def _ensure_branch(owner: str, repo: str, branch: str, github_token: str) -> None:
    headers = _headers(github_token)
    branch_url = f'https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}'
    branch_resp = requests.get(branch_url, headers=headers, timeout=30)
    if branch_resp.status_code == 200:
        return
    if branch_resp.status_code != 404:
        raise RuntimeError(f'Failed to verify branch: {branch_resp.status_code} {branch_resp.text}')

    repo_resp = requests.get(f'https://api.github.com/repos/{owner}/{repo}', headers=headers, timeout=30)
    if repo_resp.status_code != 200:
        raise RuntimeError(f'Failed to fetch repo metadata: {repo_resp.status_code} {repo_resp.text}')
    base_branch = repo_resp.json().get('default_branch', 'main')

    base_ref_url = f'https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}'
    base_ref_resp = requests.get(base_ref_url, headers=headers, timeout=30)
    if base_ref_resp.status_code != 200:
        raise RuntimeError(f'Failed to resolve base branch ref: {base_ref_resp.status_code} {base_ref_resp.text}')
    base_sha = (((base_ref_resp.json() or {}).get('object') or {}).get('sha'))
    if not base_sha:
        raise RuntimeError('Failed to determine base branch commit SHA')

    create_ref_payload = {'ref': f'refs/heads/{branch}', 'sha': base_sha}
    create_ref_resp = requests.post(
        f'https://api.github.com/repos/{owner}/{repo}/git/refs',
        headers=headers,
        json=create_ref_payload,
        timeout=30,
    )
    if create_ref_resp.status_code not in (200, 201):
        raise RuntimeError(f'Failed to create branch: {create_ref_resp.status_code} {create_ref_resp.text}')


def publish_readme(repo_url: str, readme_content: str, branch: str, commit_message: str, github_token: str, pr_title: str, pr_body: str) -> Dict[str, Any]:
    owner, repo = parse_owner_repo(repo_url)
    headers = _headers(github_token)
    _ensure_branch(owner, repo, branch, github_token)
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

    default_branch_resp = requests.get(f'https://api.github.com/repos/{owner}/{repo}', headers=headers, timeout=30)
    if default_branch_resp.status_code != 200:
        raise RuntimeError(f'Failed to fetch repo metadata: {default_branch_resp.status_code} {default_branch_resp.text}')
    base_branch = default_branch_resp.json().get('default_branch', 'main')

    pr_payload = {
        'title': pr_title,
        'body': pr_body,
        'head': branch,
        'base': base_branch,
    }
    pr_resp = requests.post(f'https://api.github.com/repos/{owner}/{repo}/pulls', headers=headers, json=pr_payload, timeout=30)
    if pr_resp.status_code not in (200, 201):
        raise RuntimeError(f'PR creation failed: {pr_resp.status_code} {pr_resp.text}')
    pr = pr_resp.json()
    return {
        'success': True,
        'repo': f'{owner}/{repo}',
        'branch': branch,
        'pr_url': pr.get('html_url'),
        'pr_number': pr.get('number'),
        'pr_title': pr.get('title'),
    }
