import os, re, json, yaml, requests
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(".env.local")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL = os.getenv("GEMINI_MODEL_NAME") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"

if not GITHUB_TOKEN:
    raise RuntimeError("Missing GITHUB_TOKEN in .env.local")

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY in .env.local")

genai.configure(api_key=GEMINI_API_KEY)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}

def parse_owner_repo(repo_url):
    m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
    if not m:
        return None, None
    return m.group(1), m.group(2).replace(".git", "")

def get_readme(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    r = requests.get(url, headers={**headers, "Accept": "application/vnd.github.raw"}, timeout=30)
    if r.status_code == 200:
        return r.text[:12000]
    return ""

def ai_summary(repo, readme):
    prompt = f"""
Return only valid JSON.

Create missing repository metadata for this project.

Repo name: {repo.get("full_name")}
Current description: {repo.get("description") or ""}
Language: {repo.get("language") or ""}

README:
{readme[:10000]}

JSON schema:
{{
  "description": "2-3 line practical enterprise description",
  "tags": ["tag1", "tag2"],
  "features": ["feature1", "feature2"],
  "tech_stack": ["tech1", "tech2"]
}}
"""
    model = genai.GenerativeModel(MODEL)
    res = model.generate_content(prompt)
    text = (res.text or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)

with open("config/repos.yaml", "r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

repos = data.get("repos", [])
updated = 0
skipped = 0

for repo in repos:
    desc = (repo.get("description") or "").strip()

    # Only enrich weak/missing descriptions
    if desc and desc.lower() not in ["no description available.", "n/a"] and len(desc) > 40:
        skipped += 1
        continue

    owner, name = parse_owner_repo(repo.get("repo_url", ""))
    if not owner:
        continue

    readme = get_readme(owner, name)
    if not readme:
        repo["description"] = desc or "No README found. Description needs manual update."
        continue

    try:
        enriched = ai_summary(repo, readme)
        repo["description"] = enriched.get("description") or desc or ""
        repo["tags"] = enriched.get("tags", [])
        repo["features"] = enriched.get("features", [])
        repo["tech_stack"] = enriched.get("tech_stack", [])
        repo["readme_available"] = True
        updated += 1
        print(f"Updated: {repo.get('full_name')}")
    except Exception as e:
        repo["enrichment_error"] = str(e)
        print(f"Failed: {repo.get('full_name')} -> {e}")

with open("config/repos.yaml", "w", encoding="utf-8") as f:
    yaml.safe_dump({"repos": repos}, f, sort_keys=False, allow_unicode=True)

print(f"Done. Updated={updated}, skipped={skipped}, total={len(repos)}")
