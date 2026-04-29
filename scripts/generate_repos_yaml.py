import os
import requests
import yaml
import urllib3
import base64
from dotenv import load_dotenv

load_dotenv(".env.local")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def sanitize_proxy_env():
    proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"]
    for var in proxy_vars:
        value = os.environ.get(var, "")
        if "127.0.0.1:9" in value or "localhost:9" in value:
            os.environ.pop(var, None)
            print(f"[WARN] Removed invalid proxy env: {var}")

sanitize_proxy_env()

token = os.getenv("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN missing in .env.local")

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
}

repos = []
page = 1

def derive_description_from_readme(owner: str, name: str, headers: dict) -> str:
    url = f"https://api.github.com/repos/{owner}/{name}/readme"
    try:
        resp = requests.get(url, headers=headers, timeout=30, verify=False)
        if resp.status_code != 200:
            return ""
        payload = resp.json()
        encoded = payload.get("content", "")
        if not encoded:
            return ""
        text = base64.b64decode(encoded).decode("utf-8", errors="replace")
        for raw_line in text.splitlines():
            line = raw_line.strip().lstrip("#").strip()
            if line and len(line) > 8:
                return line[:180]
        return ""
    except Exception:
        return ""

while True:
    url = f"https://api.github.com/user/repos?per_page=100&sort=updated&page={page}"
    response = requests.get(url, headers=headers, timeout=30, verify=False)

    if response.status_code != 200:
        raise RuntimeError(f"GitHub API failed: {response.status_code} {response.text}")

    data = response.json()
    if not data:
        break

    for repo in data:
        full_name = repo.get("full_name", "")
        owner, repo_name = full_name.split("/", 1) if "/" in full_name else ("", "")
        description = repo.get("description") or ""
        if not description and owner and repo_name:
            description = derive_description_from_readme(owner, repo_name, headers)

        repos.append({
            "name": repo.get("name"),
            "full_name": full_name,
            "repo_url": repo.get("html_url"),
            "description": description,
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
