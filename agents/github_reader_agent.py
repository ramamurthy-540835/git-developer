import os
import logging
from github import Github, GithubException
import base64
import re
from typing import List, Dict, Any, Optional
import requests
import requests.packages.urllib3 # New: for disabling SSL warnings
import urllib3 # For explicit warning disable

logging.basicConfig(level=logging.INFO)

def sanitize_proxy_env() -> None:
    """
    Removes broken proxy env settings that redirect traffic to localhost:9.
    """
    proxy_vars = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]
    for key in proxy_vars:
        value = os.environ.get(key, "")
        if "127.0.0.1:9" in value or "localhost:9" in value:
            os.environ.pop(key, None)
            logging.warning(f"Removed invalid proxy setting from {key}.")

def detect_tech_stack(files: List[str]) -> List[str]:
    """
    Detects common tech stack components based on file names.
    """
    tech_stack = set()
    for file in files:
        file_lower = file.lower()
        if "package.json" in file_lower:
            tech_stack.add("Node.js/npm")
            if "next.config." in file_lower or "next.js" in file_lower:
                tech_stack.add("Next.js")
            if "react" in file_lower: # This is a heuristic, package.json would tell more
                tech_stack.add("React")
        if "requirements.txt" in file_lower or ".venv" in file_lower:
            tech_stack.add("Python")
            if "fastapi" in file_lower or "main.py" in file_lower:
                tech_stack.add("FastAPI")
            if "flask" in file_lower:
                tech_stack.add("Flask")
        if "pom.xml" in file_lower or ".java" in file_lower:
            tech_stack.add("Java/Maven")
        if ".go" in file_lower:
            tech_stack.add("Go")
        if ".cs" in file_lower or ".csproj" in file_lower:
            tech_stack.add("C#/.NET")
        if "dockerfile" in file_lower:
            tech_stack.add("Docker")
        if ".git" in file_lower: # Just a meta-indicator
            tech_stack.add("Git")
        if "kubernetes" in file_lower or ".kube" in file_lower:
            tech_stack.add("Kubernetes")
        if ".tf" in file_lower:
            tech_stack.add("Terraform")
        if "azure" in file_lower:
            tech_stack.add("Azure")
        if "aws" in file_lower:
            tech_stack.add("AWS")
        if "gcp" in file_lower or "cloudbuild.yaml" in file_lower:
            tech_stack.add("GCP")
        if "tailwind" in file_lower or "postcss.config.js" in file_lower:
            tech_stack.add("Tailwind CSS")

    return list(tech_stack)

def _fetch_repo_context_via_rest(owner: str, repo_name: str, github_token: str, repo_url: str) -> Dict[str, Any]:
    """
    Fallback path using GitHub REST API with verify=False for environments
    with TLS interception/self-signed corporate certificates.
    """
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    repo_api = f"https://api.github.com/repos/{owner}/{repo_name}"
    repo_resp = requests.get(repo_api, headers=headers, verify=False, timeout=30)
    repo_resp.raise_for_status()
    repo_json = repo_resp.json()

    repo_description = repo_json.get("description") or "No description provided."

    readme_content = "No README.md found."
    readme_api = f"{repo_api}/readme"
    readme_resp = requests.get(readme_api, headers=headers, verify=False, timeout=30)
    if readme_resp.status_code == 200:
        readme_json = readme_resp.json()
        encoded = readme_json.get("content", "")
        if encoded:
            readme_content = base64.b64decode(encoded).decode("utf-8", errors="replace")[:8000]

    top_api = f"{repo_api}/contents"
    top_resp = requests.get(top_api, headers=headers, verify=False, timeout=30)
    top_resp.raise_for_status()
    items = top_resp.json()

    top_level_items = []
    all_files_for_tech_detection = []
    key_folders_present = []
    for item in items:
        path = item.get("path", "")
        item_type = item.get("type", "")
        top_level_items.append(path)
        all_files_for_tech_detection.append(path)
        if item_type == "dir" and path.lower() in ["frontend", "backend", "api", "agents", "scripts", "config"]:
            key_folders_present.append(path)

    features = [
        "Project setup and configuration",
        "Code organization (e.g., frontend, backend, API, agents)",
        "README documentation"
    ]
    if "frontend" in key_folders_present:
        features.append("User Interface (UI)")
    if "backend" in key_folders_present:
        features.append("Backend services/APIs")
    if "api" in key_folders_present:
        features.append("API endpoints")
    if "agents" in key_folders_present:
        features.append("Autonomous agents/scripts")
    if "scripts" in key_folders_present:
        features.append("Automation scripts")

    tech_stack_detected = detect_tech_stack(all_files_for_tech_detection + [readme_content])
    return {
        "name": repo_name,
        "description": repo_description,
        "readme": readme_content,
        "files": top_level_items,
        "tech_stack": tech_stack_detected,
        "features": features,
        "repo_url": repo_url
    }

def get_repo_context(repo_url: str) -> Dict[str, Any]:
    """
    Fetches repository context from a GitHub URL using the GitHub API.

    Args:
        repo_url (str): The URL of the GitHub repository (e.g., https://github.com/owner/repo).

    Returns:
        dict: A dictionary containing repository name, description, README content,
              top-level files/folders, detected tech stack, and a simple features list.
              Returns error information if the repository cannot be accessed.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logging.error("GITHUB_TOKEN environment variable not set. Cannot access GitHub API.")
        return {
            "name": "Error",
            "description": "GITHUB_TOKEN not set.",
            "readme": "Please set the GITHUB_TOKEN environment variable to access GitHub repositories.",
            "files": [], "tech_stack": [], "features": [], "repo_url": repo_url
        }
    
    # Temporarily disable SSL verification for requests used by PyGithub
    # This is generally NOT recommended in production due to security risks.
    # It is used here to address specific local environment SSL certificate issues.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    sanitize_proxy_env()
    try:
        # Create a requests session and disable SSL verification for it
        session = requests.Session()
        session.verify = False # 🔥 disable SSL verification

        # Extract owner and repo name from the URL
        match = re.match(r"https://github.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
        
        owner, repo_name = match.groups()
        return _fetch_repo_context_via_rest(owner, repo_name, github_token, repo_url)

    except GithubException as e:
        logging.error(f"GitHub API error for {repo_url}: {e}", exc_info=True)
        return {
            "name": "Error",
            "description": f"Failed to fetch repository: {e.data.get('message', str(e))}",
            "readme": f"Could not access repository. Details: {e.data.get('message', str(e))}",
            "files": [], "tech_stack": [], "features": [], "repo_url": repo_url
        }
    except ValueError as e:
        logging.error(f"Repository URL parsing error: {e}", exc_info=True)
        return {
            "name": "Error",
            "description": f"Invalid repository URL: {e}",
            "readme": f"Please provide a valid GitHub repository URL. Details: {e}",
            "files": [], "tech_stack": [], "features": [], "repo_url": repo_url
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred for {repo_url}: {e}", exc_info=True)
        return {
            "name": "Error",
            "description": f"An unexpected error occurred: {type(e).__name__}",
            "readme": f"An unexpected error occurred. Details: {e}",
            "files": [], "tech_stack": [], "features": [], "repo_url": repo_url
        }
