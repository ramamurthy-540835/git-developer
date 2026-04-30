import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml
from dotenv import load_dotenv
from google import genai

load_dotenv('.env.local')

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL_NAME') or os.getenv('GEMINI_MODEL') or 'gemini-2.5-flash'

if not GITHUB_TOKEN:
    raise RuntimeError('Missing GITHUB_TOKEN in .env.local')
if not GEMINI_API_KEY:
    raise RuntimeError('Missing GEMINI_API_KEY or GOOGLE_API_KEY in .env.local')

client = genai.Client(api_key=GEMINI_API_KEY)


def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    m = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not m:
        raise ValueError(f'Invalid GitHub URL: {repo_url}')
    return m.group(1), m.group(2).replace('.git', '')


def gh_get(url: str, accept: str = 'application/vnd.github+json') -> Any:
    headers = {'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': accept}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


def gh_get_text(url: str, accept: str = 'application/vnd.github.raw') -> str:
    headers = {'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': accept}
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.text
    return ''


def fetch_repo_metadata(owner: str, repo: str) -> Dict[str, Any]:
    meta = gh_get(f'https://api.github.com/repos/{owner}/{repo}')
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
    }


def fetch_tree(owner: str, repo: str, branch: str) -> List[str]:
    tree = gh_get(f'https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1')
    return [n.get('path') for n in tree.get('tree', []) if n.get('type') == 'blob' and n.get('path')]


def fetch_file(owner: str, repo: str, path: str) -> str:
    return gh_get_text(f'https://api.github.com/repos/{owner}/{repo}/contents/{path}')


def parse_requirements(text: str) -> List[Dict[str, str]]:
    deps = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        m = re.match(r'([A-Za-z0-9_.\-]+)\s*([<>=!~]{1,2}.*)?$', s)
        if m:
            deps.append({'name': m.group(1), 'spec': (m.group(2) or '').strip()})
    return deps


def parse_package_json(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return {
        'dependencies': data.get('dependencies', {}),
        'devDependencies': data.get('devDependencies', {}),
        'scripts': data.get('scripts', {}),
    }


def detect_tools(paths: List[str], requirements_deps: List[Dict[str, str]], package_data: Dict[str, Any]) -> Dict[str, Any]:
    req_names = {d['name'].lower() for d in requirements_deps}
    pkg_deps = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
    pkg_names = {k.lower() for k in pkg_deps.keys()}

    def has_any(items: List[str]) -> bool:
        return any(i in paths for i in items)

    test_tools = []
    lint_tools = []
    format_tools = []
    ci_cd = []

    if 'pytest' in req_names or 'pytest' in pkg_names or has_any(['pytest.ini']):
        test_tools.append('pytest')
    if 'tox' in req_names or has_any(['tox.ini']):
        test_tools.append('tox')
    if 'ruff' in req_names or 'ruff' in pkg_names or has_any(['ruff.toml', 'pyproject.toml']):
        lint_tools.append('ruff')
    if 'flake8' in req_names or has_any(['.flake8']):
        lint_tools.append('flake8')
    if 'eslint' in pkg_names:
        lint_tools.append('eslint')
    if 'black' in req_names:
        format_tools.append('black')
    if 'prettier' in pkg_names:
        format_tools.append('prettier')
    if any(p.startswith('.github/workflows/') for p in paths):
        ci_cd.append('GitHub Actions')

    return {
        'test_tools': sorted(set(test_tools)),
        'lint_tools': sorted(set(lint_tools)),
        'format_tools': sorted(set(format_tools)),
        'ci_cd': sorted(set(ci_cd)),
        'has_tests': any('test' in p.lower() for p in paths),
        'has_ci': bool(ci_cd),
    }


def extract_real_commands(paths: List[str], package_data: Dict[str, Any]) -> List[str]:
    cmds = []
    for name, cmd in package_data.get('scripts', {}).items():
        cmds.append(f'npm run {name}  # {cmd}')
    if 'scripts/run_pipeline.py' in paths:
        cmds.append('python3 scripts/run_pipeline.py')
    if 'scripts/generate_repos_yaml.py' in paths:
        cmds.append('python3 scripts/generate_repos_yaml.py --repo-url https://github.com/<owner>/<repo>')
    if 'scripts/enrich_repos_yaml.py' in paths:
        cmds.append('python3 scripts/enrich_repos_yaml.py --config config/repos.yaml --output config/repo_profile.yaml')
    if 'scripts/generate_readme_drafts.py' in paths:
        cmds.append('python3 scripts/generate_readme_drafts.py --input config/repo_profile.yaml --output generated_readmes/<repo>/README.md')
    return cmds


def find_competitors(repo_name: str) -> List[Dict[str, Any]]:
    q = f'{repo_name} git automation in:name,description'
    data = gh_get(f'https://api.github.com/search/repositories?q={requests.utils.quote(q)}&sort=stars&order=desc&per_page=5')
    items = data.get('items', [])
    out = []
    for it in items[:3]:
        out.append({
            'name': it.get('full_name'),
            'url': it.get('html_url'),
            'stars': it.get('stargazers_count', 0),
            'positioning': it.get('description') or '',
        })
    return out


def build_profile_with_ai(facts: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
Return only valid JSON.
Use the verified analysis below to build an industry-standard README profile.
Do not invent commands; only use provided real_commands.

FACTS:
{json.dumps(facts, indent=2)}

ANALYSIS:
{json.dumps(analysis, indent=2)}

JSON schema:
{{
  "overview": "2-3 sentence value proposition",
  "problem_statement": "2-3 sentence problem framing",
  "key_features": ["max 5 repo-specific bullets"],
  "tech_stack_summary": "single paragraph with real tools and versions when available",
  "architecture_summary": "short repo-specific architecture summary",
  "quick_start_steps": ["4-6 verified setup/run steps"],
  "best_practices": ["3-5 do/don't bullets for this repo usage"],
  "competitive_analysis": {{
    "summary": "how this differs from competitors",
    "differentiators": ["3 bullets"]
  }},
  "contributing": "short contributing guidance",
  "license": "license or TBD"
}}
"""
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = (response.text or '').strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(description='Enrich single project with real repo analysis for README generation')
    parser.add_argument('--config', default='config/repos.yaml')
    parser.add_argument('--output', default='config/repo_profile.yaml')
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding='utf-8')) or {}
    project = config.get('project') or {}
    repo_url = project.get('repo_url')
    if not repo_url:
        raise RuntimeError('Missing project.repo_url in config/repos.yaml')

    owner, repo = parse_owner_repo(repo_url)
    facts = fetch_repo_metadata(owner, repo)
    paths = fetch_tree(owner, repo, facts['default_branch'])

    req_text = fetch_file(owner, repo, 'requirements.txt') if 'requirements.txt' in paths else ''
    pkg_text = fetch_file(owner, repo, 'package.json') if 'package.json' in paths else ''
    readme_excerpt = gh_get_text(f'https://api.github.com/repos/{owner}/{repo}/readme')[:12000]

    requirements_deps = parse_requirements(req_text)
    package_data = parse_package_json(pkg_text) if pkg_text else {}
    tool_detection = detect_tools(paths, requirements_deps, package_data)
    real_commands = extract_real_commands(paths, package_data)
    competitors = find_competitors(repo)

    analysis = {
        'readme_excerpt': readme_excerpt,
        'files_sample': paths[:200],
        'python_dependencies': requirements_deps,
        'node_dependencies': {
            'dependencies': package_data.get('dependencies', {}),
            'devDependencies': package_data.get('devDependencies', {}),
        },
        'tool_detection': tool_detection,
        'real_commands': real_commands,
        'competitors': competitors,
    }

    ai_profile = build_profile_with_ai(facts, analysis)

    output = {
        'project': {'owner': owner, 'repo': repo, **facts},
        'analysis': analysis,
        'repo_profile': ai_profile,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(output, sort_keys=False, allow_unicode=True), encoding='utf-8')
    print(f'Wrote enriched profile to {out_path}')


if __name__ == '__main__':
    main()
