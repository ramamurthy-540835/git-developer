import argparse
from pathlib import Path
import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="Create repo config for a single target repository.")
    parser.add_argument(
        "--repo-url",
        default="https://github.com/ramamurthy-540835/git-developer",
        help="Target GitHub repository URL.",
    )
    parser.add_argument(
        "--output",
        default="config/repos.yaml",
        help="Output YAML path.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    owner_repo = args.repo_url.rstrip("/").split("github.com/")[-1]
    owner, repo = owner_repo.split("/", 1)

    payload = {
        "project": {
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "repo_url": args.repo_url,
        }
    }

    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)

    print(f"Wrote single-project config to {output_path}")


if __name__ == "__main__":
    main()
