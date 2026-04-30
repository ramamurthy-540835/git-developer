from typing import Any, Dict


def _read_time_minutes(text: str) -> int:
    words = len(text.split())
    return max(1, round(words / 220))


def readme_composer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    rp = state.get('repo_profile', {})
    meta = rp.get('meta', {})
    tech = rp.get('tech_stack', {})
    competitors = (state.get('competitors') or {}).get('competitors', [])
    usp = (state.get('competitors') or {}).get('unique_selling_points', [])
    bp = state.get('best_practices', {})
    commands = rp.get('real_commands', [])

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

    markdown = f"""# {meta.get('name') or 'Project'}

> Editable README template generated from LangGraph workflow.

{meta.get('description') or 'TODO: Add clear project overview.'}

## Problem Statement

TODO: Describe the specific problem this project solves.

## Key Features

- TODO: Add 3-5 verified features from code.

## Real Tech Stack

{chr(10).join(tech_lines)}

## Quick Start

```bash
{chr(10).join(commands) if commands else '# TODO: add verified commands'}
```

## Competitive Analysis

### Comparable Tools

{chr(10).join(comp_lines)}

### What Makes This Project Different

{chr(10).join(f'- {x}' for x in usp) if usp else '- TODO: Add differentiators'}

## Best Practices

### Do

{chr(10).join(f'- {x}' for x in bp.get('dos', [])) or '- TODO'}

### Avoid

{chr(10).join(f'- {x}' for x in bp.get('donts', [])) or '- TODO'}

## Contributing

TODO: Add contribution and review workflow.

## License

TODO
"""

    completeness = 85 if commands else 65
    uniqueness = 80 if usp else 60
    metrics = {
        'quality_score': round((completeness + uniqueness) / 2),
        'completeness': completeness,
        'uniqueness_score': uniqueness,
        'estimated_read_time_min': _read_time_minutes(markdown),
    }

    state['readme_markdown'] = markdown
    state['metrics'] = metrics
    state['progress'].append({'stage': 'compose_readme', 'percent': 100, 'message': 'README composed'})
    return state
