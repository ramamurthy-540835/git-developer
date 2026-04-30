import argparse
import re
from pathlib import Path
from typing import Any, Dict, List

import os
import base64
import requests
import yaml
from dotenv import load_dotenv

load_dotenv('.env.local')

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')


def _bullets(items: List[str]) -> str:
    clean = [x.strip() for x in items if str(x).strip()]
    if not clean:
        return '- Not detected from repository files.'
    return '\n'.join(f'- {x}' for x in clean)


def _score(profile: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    notes = []
    if profile.get('overview'):
        score += 15
    else:
        notes.append('Add a stronger overview.')
    if profile.get('problem_statement'):
        score += 10
    else:
        notes.append('Add a clear problem statement.')
    if profile.get('key_features'):
        score += 15
    else:
        notes.append('Add repo-specific key features.')
    if analysis.get('python_dependencies') or analysis.get('node_dependencies', {}).get('dependencies'):
        score += 15
    else:
        notes.append('No dependency files detected.')
    if analysis.get('tool_detection', {}).get('has_ci'):
        score += 10
    else:
        notes.append('No CI pipeline detected.')
    if analysis.get('real_commands'):
        score += 15
    else:
        notes.append('No verified runnable commands found.')
    if profile.get('competitive_analysis', {}).get('summary'):
        score += 10
    else:
        notes.append('Competitive analysis is weak or missing.')
    if profile.get('best_practices'):
        score += 10
    else:
        notes.append('Best practices section missing.')
    return {'score': min(score, 100), 'industry_target': 90, 'notes': notes[:4]}


def _extract_section(markdown: str, title: str) -> str:
    if not markdown:
        return ''
    pattern = rf"(?ims)^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)"
    m = re.search(pattern, markdown)
    return m.group(1).strip() if m else ''


def build_readme(data: Dict[str, Any], existing_readme: str = '') -> str:
    project = data.get('project', {})
    analysis = data.get('analysis', {})
    profile = data.get('repo_profile', {})

    repo_name = project.get('name') or project.get('repo') or 'git-developer'
    repo_url = project.get('repo_url') or ''

    py_deps = analysis.get('python_dependencies', [])
    node_deps = analysis.get('node_dependencies', {})
    tools = analysis.get('tool_detection', {})
    commands = analysis.get('real_commands', [])
    competitors = analysis.get('competitors', [])

    tech_lines = []
    if py_deps:
        tech_lines.append('- Python dependencies: ' + ', '.join(f"{d.get('name')}{d.get('spec', '')}".strip() for d in py_deps[:12]))
    if node_deps.get('dependencies'):
        tech_lines.append('- Node dependencies: ' + ', '.join(f'{k}@{v}' for k, v in list(node_deps['dependencies'].items())[:12]))
    if tools.get('test_tools'):
        tech_lines.append('- Testing: ' + ', '.join(tools['test_tools']))
    if tools.get('lint_tools'):
        tech_lines.append('- Linting: ' + ', '.join(tools['lint_tools']))
    if tools.get('format_tools'):
        tech_lines.append('- Formatting: ' + ', '.join(tools['format_tools']))
    if tools.get('ci_cd'):
        tech_lines.append('- CI/CD: ' + ', '.join(tools['ci_cd']))
    if not tech_lines:
        tech_lines = ['- Not detected from repository files.']

    competitor_lines = [f"- [{c.get('name')}]({c.get('url')}): {c.get('positioning') or 'No description'} (⭐ {c.get('stars', 0)})" for c in competitors] or ['- No comparable repositories were detected automatically.']

    quality = _score(profile, analysis)

    existing_notes = _extract_section(existing_readme, 'Project Notes')

    lines = [
        f'# {repo_name}',
        '',
        '> Editable README template generated from real repo analysis.',
        '> Replace or refine any section marked with `TODO`.',
        '',
        profile.get('overview') or 'TODO: Add clear 2-3 sentence overview.',
        '',
        '## Problem Statement',
        '',
        profile.get('problem_statement') or 'TODO: Add the problem this project solves.',
        '',
        '## Key Features',
        '',
        _bullets(profile.get('key_features', [])[:5]) if profile.get('key_features') else '- TODO: Add 3-5 real features from code.',
        '',
        '## Real Tech Stack Analysis',
        '',
        '\n'.join(tech_lines),
        '',
        '## Quick Start',
        '',
        _bullets(profile.get('quick_start_steps', [])) if profile.get('quick_start_steps') else '- TODO: Add install and run steps that were tested.',
        '',
        '### Verified Commands from Repository',
        '',
        '```bash',
        '\n'.join(commands[:12]) if commands else '# TODO: Add verified commands from scripts/docs',
        '```',
        '',
        '## Competitive Analysis',
        '',
        profile.get('competitive_analysis', {}).get('summary') or 'TODO: Add how this project differs from alternatives.',
        '',
        '### Comparable Tools',
        '',
        '\n'.join(competitor_lines),
        '',
        '### Differentiators',
        '',
        _bullets(profile.get('competitive_analysis', {}).get('differentiators', [])) if profile.get('competitive_analysis', {}).get('differentiators') else '- TODO: Add 2-3 unique differentiators.',
        '',
        '## Best Practices',
        '',
        _bullets(profile.get('best_practices', [])) if profile.get('best_practices') else '- TODO: Add 3-5 do/don\'t best practices.',
        '',
        '## README Quality Score',
        '',
        f"- Score: {quality['score']}/100",
        f"- Industry target: {quality['industry_target']}/100",
        '',
        '## Project Notes',
        '',
        existing_notes or 'TODO: Add project-specific notes, caveats, and roadmap.',
        '',
        '## Contributing',
        '',
        profile.get('contributing') or 'TODO: Add contribution workflow (branching, PR checks, review expectations).',
        '',
        '## License',
        '',
        profile.get('license') or 'TBD',
        '',
        f'Repository: {repo_url}' if repo_url else '',
    ]
    return '\n'.join(x for x in lines if x is not None).strip() + '\n'


def publish_readme_to_github(repo_url: str, readme_content: str, branch: str, commit_message: str) -> None:
    if not GITHUB_TOKEN:
        raise RuntimeError('Missing GITHUB_TOKEN in .env.local')
    m = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not m:
        raise RuntimeError(f'Invalid repo URL: {repo_url}')
    owner, repo = m.group(1), m.group(2).replace('.git', '')

    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json',
    }

    get_url = f'https://api.github.com/repos/{owner}/{repo}/contents/README.md?ref={branch}'
    get_resp = requests.get(get_url, headers=headers, timeout=30)
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json().get('sha')
    elif get_resp.status_code not in (404,):
        raise RuntimeError(f'Failed to check README on branch {branch}: {get_resp.status_code} {get_resp.text}')

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
        raise RuntimeError(f'Failed to publish README: {put_resp.status_code} {put_resp.text}')

    print(f'Published README.md to {owner}/{repo} on branch {branch}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate editable README template from enriched analysis')
    parser.add_argument('--input', default='config/repo_profile.yaml')
    parser.add_argument('--output', default='generated_readmes/git-developer/README.md')
    parser.add_argument('--existing-readme', default='README.md')
    parser.add_argument('--write-root-readme', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--branch', default='main')
    parser.add_argument('--commit-message', default='docs: update generated README')
    args = parser.parse_args()

    data = yaml.safe_load(Path(args.input).read_text(encoding='utf-8')) or {}
    existing = ''
    existing_path = Path(args.existing_readme)
    if existing_path.exists():
        existing = existing_path.read_text(encoding='utf-8')

    readme = build_readme(data, existing_readme=existing)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(readme, encoding='utf-8')
    print(f'Wrote README draft: {out_path}')

    if args.write_root_readme:
        Path('README.md').write_text(readme, encoding='utf-8')
        print('Updated root README.md')

    if args.publish:
        repo_url = (data.get('project', {}) or {}).get('repo_url')
        if not repo_url:
            raise RuntimeError('Missing project.repo_url in input profile')
        publish_readme_to_github(repo_url, readme, args.branch, args.commit_message)


if __name__ == '__main__':
    main()
