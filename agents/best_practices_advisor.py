from typing import Any, Dict


def best_practices_advisor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    tech = (state.get('repo_profile') or {}).get('tech_stack', {})
    has_ci = tech.get('has_ci', False)

    dos = [
        'Use feature branches and PR reviews for README updates.',
        'Keep generated README sections evidence-based from repo files.',
        'Validate setup commands before publishing README changes.',
    ]
    donts = [
        'Do not publish placeholder commands that are not runnable.',
        'Do not overwrite manual project notes without review.',
    ]
    testing_tips = [
        'Run script syntax checks before pipeline execution.',
        'Add CI checks for README generation drift when possible.',
    ]
    deployment_tips = [
        'Publish README updates to a branch first, then open PR.',
        'Use protected main branch with required checks.',
    ]
    if not has_ci:
        deployment_tips.append('Set up GitHub Actions for automated validation.')

    state['best_practices'] = {
        'dos': dos,
        'donts': donts,
        'testing_tips': testing_tips,
        'deployment_tips': deployment_tips,
        'docs': [
            'https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes',
            'https://docs.github.com/en/actions',
        ],
    }
    state['progress'].append({'stage': 'best_practices', 'percent': 80, 'message': 'Best practices generated'})
    return state
