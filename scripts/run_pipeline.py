import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    run([sys.executable, "scripts/generate_repos_yaml.py", "--repo-url", "https://github.com/ramamurthy-540835/git-developer"])
    run([sys.executable, "scripts/enrich_repos_yaml.py", "--config", "config/repos.yaml", "--output", "config/repo_profile.yaml"])
    run([sys.executable, "scripts/generate_readme_drafts.py", "--input", "config/repo_profile.yaml", "--output", "generated_readmes/git-developer/README.md"])
    print("README pipeline completed for git-developer")


if __name__ == "__main__":
    main()
