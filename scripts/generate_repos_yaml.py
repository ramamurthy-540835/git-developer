import os
import requests
import yaml
from dotenv import load_dotenv

load_dotenv(".env.local")

token = os.getenv("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN missing in .env.local")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
}

repos = []
page = 1

while True:
    url = f"https://api.github.com/user/repos?per_page=100&sort=updated&page={page}"
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"GitHub API failed: {response.status_code} {response.text}")

    data = response.json()
    if not data:
        break

    for repo in data:
        repos.append({
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "repo_url": repo.get("html_url"),
            "description": repo.get("description") or "",
            "private": repo.get("private"),
            "updated_at": repo.get("updated_at"),
            "language": repo.get("language") or "",
        })

    page += 1

output = {"repos": repos}

os.makedirs("config", exist_ok=True)

with open("config/repos.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump(output, f, sort_keys=False, allow_unicode=True)

print(f"Generated config/repos.yaml with {len(repos)} repos")
for repo in repos[:20]:
    print(f"- {repo['full_name']} ({repo['language']})")
