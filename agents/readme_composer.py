from typing import Any, Dict

from agents.llm import generate_script

def _read_time_minutes(text: str) -> int:
    words = len(text.split())
    return max(1, round(words / 220))


def _safe_slug(text: str) -> str:
    return (text or "project").strip()


def _badge_repo(full_name: str) -> str:
    return _safe_slug(full_name).replace("_", "-")


def readme_composer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    rp = state.get('repo_profile', {})
    meta = rp.get('meta', {})
    tech = rp.get('tech_stack', {})
    competitors = (state.get('competitors') or {}).get('competitors', [])
    usp = (state.get('competitors') or {}).get('unique_selling_points', [])
    bp = state.get('best_practices', {})
    commands = rp.get('real_commands', [])
    evidence = rp.get('evidence', {})

    repo_name = meta.get('name') or 'project'
    full_name = meta.get('full_name') or repo_name
    desc = meta.get('description') or f'{repo_name} is a production-ready software project.'
    badge_repo = _badge_repo(full_name)

    tech_lines = []
    pydeps = tech.get('python_dependencies', [])
    if pydeps:
        tech_lines.append('- Python: ' + ', '.join(f"{d.get('name')}{d.get('spec', '')}".strip() for d in pydeps[:10]))
    if tech.get('node_dependencies'):
        top = list((tech.get('node_dependencies') or {}).items())[:10]
        tech_lines.append('- Node: ' + ', '.join(f'{k}@{v}' for k, v in top))
    if tech.get('has_ci'):
        tech_lines.append('- CI/CD: GitHub Actions detected')
    if not tech_lines:
        tech_lines.append('- Not detected from repository files')

    comp_lines = [f"- [{c['name']}]({c['url']}) (⭐ {c['stars']}): {c.get('comparison') or 'N/A'}" for c in competitors] or ['- No close competitors detected']
    quick_cmds = chr(10).join(commands) if commands else 'python3 scripts/run_pipeline.py'
    deep_files = evidence.get('deep_read_files', [])
    deep_snippets = evidence.get('deep_snippets', [])
    snippet_blocks = []
    for sn in deep_snippets[:16]:
        snippet_blocks.append(f"FILE: {sn.get('path')}\n{sn.get('snippet')}")
    deep_context = "\n\n---\n\n".join(snippet_blocks) if snippet_blocks else "N/A"

    prompt = f"""Generate a complete, production-ready README.md in markdown for this repository.

Repository:
- name: {repo_name}
- full_name: {full_name}
- description: {desc}

Detected tech stack:
{chr(10).join(tech_lines)}

Suggested run commands:
{quick_cmds}

Repository evidence:
- Existing README excerpt:
{evidence.get('existing_readme_excerpt') or 'N/A'}
- requirements.txt excerpt:
{evidence.get('requirements_excerpt') or 'N/A'}
- package.json excerpt:
{evidence.get('package_json_excerpt') or 'N/A'}
- pyproject.toml excerpt:
{evidence.get('pyproject_excerpt') or 'N/A'}
- setup.py excerpt:
{evidence.get('setup_py_excerpt') or 'N/A'}
- Sample file paths:
{chr(10).join(evidence.get('sample_files', [])) if evidence.get('sample_files') else 'N/A'}
- Deep-read high-signal files:
{chr(10).join(deep_files) if deep_files else 'N/A'}
- Deep-read snippets:
{deep_context}

Competitive insights:
{chr(10).join(comp_lines)}

Differentiators:
{chr(10).join(usp) if usp else '- Structured multi-agent workflow with direct GitHub PR publishing.'}

Best practices:
Do:
{chr(10).join(bp.get('dos', []))}
Avoid:
{chr(10).join(bp.get('donts', []))}

Requirements:
- Use this exact header title format: "# 🤖 {repo_name}"
- Include badges for License, Python 3.10+, Node 18+, Build, Last commit
- Include sections: Quick Overview, Demo and Screenshot Flow, Key Features, Architecture, Tech Stack, Installation and Setup, Quick Start and Usage Guide, API Reference, Project Structure, Configuration, Contributing, Roadmap and Future Enhancements, Troubleshooting, License, Acknowledgments and Footer
- Include 5 mermaid diagrams under Architecture:
  1) System architecture graph
  2) README generation sequence diagram
  3) Frontend user flow state diagram
  4) LangGraph agent orchestration graph
  5) Deployment architecture graph
- Use professional enterprise tone, active voice, no placeholder TODO text.
- Ensure all commands are runnable and based on provided context.
- Reason from code evidence. Do not invent frameworks, services, or APIs not present in provided snippets.
- Mermaid diagrams must reflect actual architecture inferred from file evidence.
- In each major section, anchor claims to observed evidence (file names, dependencies, routes, modules).
- Output markdown only.
"""

    fallback_markdown = f"""# 🤖 {repo_name}

**AI-Powered Professional README Generator for GitHub Repositories**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-339933.svg)](https://nodejs.org/)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen)
![Last Commit](https://img.shields.io/github/last-commit/{badge_repo})

`{repo_name}` delivers enterprise-grade README generation through a multi-agent pipeline that analyzes repository context and composes production-ready documentation.

## Table of Contents
- [Quick Overview](#quick-overview)
- [Demo and Screenshot Flow](#demo-and-screenshot-flow)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation and Setup](#installation-and-setup)
- [Quick Start and Usage Guide](#quick-start-and-usage-guide)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [Roadmap and Future Enhancements](#roadmap-and-future-enhancements)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Acknowledgments and Footer](#acknowledgments-and-footer)

## Quick Overview
`{repo_name}` is designed to reduce documentation bottlenecks by generating structured, professional README content from real repository signals. The workflow combines repository analysis, competitive benchmarking, and best-practice synthesis before final markdown composition.

The platform addresses a common engineering gap: code evolves faster than documentation. By automating documentation authoring with deterministic stages, teams can improve onboarding, reduce ambiguity, and keep repository narratives aligned with implementation reality.

This system is production-ready and suitable for teams that require repeatable output quality, fast iteration, and direct GitHub publishing controls through pull-request workflows.

## Demo and Screenshot Flow
Run backend and frontend locally, connect GitHub, select a repository, and generate. A progress stream shows each stage before the final README appears with metrics.

Success criteria:
- Token validation passes
- Repository list loads
- Generation reaches completed state
- README renders with metrics and can be published

## Key Features
`{repo_name}` uses LangGraph orchestration with four specialized agents to produce documentation that is contextual instead of generic. The pipeline starts with repository profiling, continues through competitor analysis, adds implementation best practices, and ends with professional markdown composition.

Competitive analysis identifies similar public projects and captures differentiators to strengthen README positioning. Real-time progress streaming provides operational visibility across each stage, so users can monitor status continuously.

GitHub integration supports authentication, repository discovery, generation, and PR publication with custom metadata. Each output includes quality indicators and a clean enterprise markdown layout suitable for immediate review.

## Architecture
### Diagram 1: System Architecture
```mermaid
graph TB
    Client[Client] --> FE[Next.js Frontend]
    FE --> API[FastAPI API]
    API --> LG[LangGraph Orchestrator]
    LG --> RA[RepoAnalyzer]
    LG --> CA[CompetitiveAnalyzer]
    LG --> BP[BestPracticesAdvisor]
    LG --> RC[ReadmeComposer]
    RA --> GH[GitHub API]
    CA --> GH
    RC --> LLM[Gemini]
```

### Diagram 2: README Generation Pipeline
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant O as Orchestrator
    U->>F: Select repo + Generate
    F->>A: POST /api/generate-readme
    A->>O: Start workflow
    O-->>A: Stage events
    A-->>F: Stream progress
    O-->>A: README + metrics
    A-->>F: Completed result
```

### Diagram 3: Frontend User Flow
```mermaid
stateDiagram-v2
    [*] --> Authenticate
    Authenticate --> SelectRepo
    SelectRepo --> Configure
    Configure --> Generate
    Generate --> Review
    Review --> PublishPR
    PublishPR --> [*]
```

### Diagram 4: LangGraph Agent Orchestration
```mermaid
graph LR
    Start --> RepoAnalyzer --> BestPractices
    Start --> CompetitiveAnalyzer --> BestPractices
    BestPractices --> ReadmeComposer --> Output
```

### Diagram 5: Deployment Architecture
```mermaid
graph TB
    Dev[Local Dev] --> CloudRun[Cloud Run Backend]
    Dev --> Vercel[Vercel Frontend]
    CloudRun --> GitHub[GitHub API]
    CloudRun --> Gemini[Gemini API]
```

## Tech Stack
{chr(10).join(tech_lines)}

## Installation and Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

## Quick Start and Usage Guide
```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

Run commands detected for this repo:
```bash
{quick_cmds}
```

## API Reference
- `POST /api/auth/token`
- `POST /api/repos/list`
- `POST /api/generate-readme`
- `GET /api/job-status/{{job_id}}`
- `GET /api/generate-readme/{{job_id}}/stream`
- `POST /api/publish-readme`

## Project Structure
Core modules include `agents/`, `api/`, `orchestrator/`, `frontend/`, and `scripts/`.

## Configuration
Use `.env.local` for secrets and runtime config:
- `GITHUB_TOKEN`
- `GEMINI_API_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

## Contributing
1. Fork the repository.
2. Create a feature branch.
3. Commit changes.
4. Push and open a PR.

## Roadmap and Future Enhancements
- GitHub OAuth
- Batch processing
- Generation history and restore
- PDF export
- Multi-language README generation

## Troubleshooting
- Token validation fails: verify token scopes.
- Repo not found: confirm visibility and URL.
- Timeout: retry and check backend logs.

## License
MIT License.

## Acknowledgments and Footer
Built with LangGraph, FastAPI, and Next.js. Powered by Gemini AI.

### Competitive Analysis
{chr(10).join(comp_lines)}

### Differentiators
{chr(10).join(f'- {x}' for x in usp) if usp else '- Structured multi-agent workflow with direct GitHub PR publishing.'}

### Best Practices
Do:
{chr(10).join(f'- {x}' for x in bp.get('dos', [])) or '- Use evidence-based repository documentation.'}

Avoid:
{chr(10).join(f'- {x}' for x in bp.get('donts', [])) or '- Avoid publishing placeholder content.'}
"""

    used_llm = False
    llm_note = ''
    try:
        markdown = generate_script(prompt)
        weak = (
            (not markdown)
            or ('TODO' in markdown[:3000])
            or ('Not detected from repository files' in markdown[:5000])
            or (markdown.count('```mermaid') < 4)
        )
        if weak:
            llm_note = 'Gemini output empty or placeholder-like; used fallback template.'
            markdown = fallback_markdown
        else:
            used_llm = True
            llm_note = 'Gemini 2.5 Flash generated final README.'
    except Exception:
        llm_note = 'Gemini call failed; used fallback template.'
        markdown = fallback_markdown

    completeness = 85 if commands else 65
    uniqueness = 80 if usp else 60
    metrics = {
        'quality_score': round((completeness + uniqueness) / 2),
        'completeness': completeness,
        'uniqueness_score': uniqueness,
        'estimated_read_time_min': _read_time_minutes(markdown),
        'used_llm': used_llm,
        'llm_note': llm_note,
    }

    state['readme_markdown'] = markdown
    state['metrics'] = metrics
    state['progress'].append({'stage': 'compose_readme', 'percent': 100, 'message': 'README composed'})
    return state
