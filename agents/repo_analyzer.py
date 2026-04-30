import json
import re
from typing import Any, Dict, List

from agents.shared_github import parse_owner_repo, fetch_repo_metadata, fetch_tree, fetch_file


def _parse_requirements(text: str) -> List[Dict[str, str]]:
    deps = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        m = re.match(r'([A-Za-z0-9_.\-]+)\s*([<>=!~]{1,2}.*)?$', s)
        if m:
            deps.append({'name': m.group(1), 'spec': (m.group(2) or '').strip()})
    return deps


def _parse_package_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return {
        'dependencies': data.get('dependencies', {}),
        'devDependencies': data.get('devDependencies', {}),
        'scripts': data.get('scripts', {}),
    }


def _is_high_signal_file(path: str) -> bool:
    p = path.lower()
    if p.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.java', '.rs')):
        return True
    if p.endswith(('.yml', '.yaml', '.toml', '.json', '.md', '.sh', '.dockerfile')):
        return True
    if p in ('dockerfile', 'makefile'):
        return True
    if '/workflows/' in p or p.startswith('.github/'):
        return True
    if any(k in p for k in ('readme', 'requirements', 'pyproject', 'setup.py', 'package.json')):
        return True
    return False


def repo_analyzer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    repo_url = state['repo_url']
    token = state['github_token']
    owner, repo = parse_owner_repo(repo_url)

    meta = fetch_repo_metadata(owner, repo, token)
    paths = fetch_tree(owner, repo, meta['default_branch'], token)

    req_text = fetch_file(owner, repo, 'requirements.txt', token) if 'requirements.txt' in paths else ''
    pkg_text = fetch_file(owner, repo, 'package.json', token) if 'package.json' in paths else ''
    pyproject_text = fetch_file(owner, repo, 'pyproject.toml', token) if 'pyproject.toml' in paths else ''
    setup_text = fetch_file(owner, repo, 'setup.py', token) if 'setup.py' in paths else ''
    readme_existing = fetch_file(owner, repo, 'README.md', token) if 'README.md' in paths else ''

    req_deps = _parse_requirements(req_text)
    pkg = _parse_package_json(pkg_text)

    commands = []
    for name in (pkg.get('scripts') or {}).keys():
        commands.append(f'npm run {name}')
    if 'scripts/run_pipeline.py' in paths:
        commands.append('python3 scripts/run_pipeline.py')

    prioritized = [p for p in paths if _is_high_signal_file(p)]
    deep_paths = prioritized[:40]
    deep_snippets: List[Dict[str, str]] = []
    for p in deep_paths:
        try:
            content = fetch_file(owner, repo, p, token)
            if not content:
                continue
            snippet = '\n'.join(content.splitlines()[:120])[:5000]
            deep_snippets.append({'path': p, 'snippet': snippet})
        except Exception:
            continue

    state['repo_profile'] = {
        'meta': meta,
        'files': paths[:400],
        'tech_stack': {
            'python_dependencies': req_deps,
            'node_dependencies': pkg.get('dependencies', {}),
            'node_dev_dependencies': pkg.get('devDependencies', {}),
            'has_pyproject': bool(pyproject_text),
            'has_setup_py': bool(setup_text),
            'has_dockerfile': 'Dockerfile' in paths,
            'has_ci': any(p.startswith('.github/workflows/') for p in paths),
            'has_tests': any('test' in p.lower() for p in paths),
        },
        'entry_points': [p for p in paths if p.endswith('main.py') or p.endswith('page.js')][:20],
        'real_commands': commands,
        'evidence': {
            'existing_readme_excerpt': '\n'.join(readme_existing.splitlines()[:80])[:5000] if readme_existing else '',
            'requirements_excerpt': req_text[:3000],
            'package_json_excerpt': pkg_text[:3000],
            'pyproject_excerpt': pyproject_text[:3000],
            'setup_py_excerpt': setup_text[:3000],
            'sample_files': paths[:80],
            'deep_read_files': deep_paths,
            'deep_snippets': deep_snippets,
        },
    }
    state['progress'].append({'stage': 'repo_analyzer', 'percent': 40, 'message': 'Repository analysis complete'})
    return state
