import os
import logging
from github import Github, GithubException
import base64
import re
from typing import List, Dict, Any, Optional
import requests.packages.urllib3 # New: for disabling SSL warnings
import urllib3 # For explicit warning disable

logging.basicConfig(level=logging.INFO)

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
    os.environ["REQUESTS_KWARGS"] = '{"verify": false}'

    try:
        g = Github(github_token)
        # The PyGithub library uses the requests library internally, which
        # will pick up the REQUESTS_KWARGS environment variable if set.
        # Extract owner and repo name from the URL
        match = re.match(r"https://github.com/([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
        
        owner, repo_name = match.groups()
        repo = g.get_user(owner).get_repo(repo_name)

        repo_description = repo.description if repo.description else "No description provided."
        
        readme_content = ""
        try:
            readme = repo.get_readme()
            readme_content = base64.b64decode(readme.content).decode('utf-8')
            readme_content = readme_content[:8000] # Limit README size
        except GithubException:
            logging.warning(f"No README.md found for {repo_url}")
            readme_content = "No README.md found."

        contents = repo.get_contents("")
        top_level_items = []
        all_files_for_tech_detection = []
        key_folders_present = []

        for content_file in contents:
            top_level_items.append(content_file.path)
            all_files_for_tech_detection.append(content_file.path)
            if content_file.type == "dir":
                if content_file.path.lower() in ["frontend", "backend", "api", "agents", "scripts", "config"]:
                    key_folders_present.append(content_file.path)
            # For deeper tech stack detection, could recurse into common dirs
            # For now, just top level items.

        # Heuristic for features - could be improved with LLM later
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
        
        # Detect tech stack based on all file names (top-level only for now)
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
