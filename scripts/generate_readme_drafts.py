import os
import argparse
import logging
import yaml
import os
import argparse
import logging
import yaml
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
import sys
import json
import time
import base64
import requests # New: for GitHub REST API calls

# Automatically add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure google.generativeai is imported
try:
    import google.generativeai as genai
except ImportError:
    logging.error("google-generativeai not found. Please install it: pip install google-generativeai")
    sys.exit(1)

# Import github_reader_agent safely after sys.path fix
github_reader_agent = None
try:
    from agents.github_reader_agent import get_repo_context
    github_reader_agent = get_repo_context
except ImportError:
    logging.warning("agents.github_reader_agent not found. GitHub repository context will not be used for README generation.")
except Exception as e:
    logging.warning(f"Failed to load github_reader_agent: {e}. GitHub repository context will not be used for README generation.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env.local
load_dotenv(dotenv_path='./.env.local')

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set. Please set it in .env.local.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)

def generate_readme_content(repo_metadata: Dict[str, Any], github_repo_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Generates a concise and practical README markdown content using Gemini,
    based on repository metadata and, if available, GitHub repository context.
    """
    repo_name = repo_metadata.get("name", "Unnamed Project").replace('-', ' ').replace('_', ' ').title()
    full_name = repo_metadata.get("full_name", "owner/repo")
    description = repo_metadata.get("description", "A comprehensive project.")
    repo_url = repo_metadata.get("repo_url", "https://github.com/owner/repo")
    language = repo_metadata.get("language", "Not specified")
    tags = ", ".join(repo_metadata.get("tags", [])) if repo_metadata.get("tags") else "N/A"

    prompt_parts = [
        f"Generate ONLY a professional and practical GitHub README.md in markdown format. Do not include any extra commentary, introductory/concluding remarks, or non-markdown text.",
        f"The README should clearly explain the project and be structured with the following sections:",
        f"# {repo_name}",
        f"## Overview",
        f"## Business Problem",
        f"## Key Capabilities",
        f"## Architecture",
        f"## Tech Stack",
        f"## Repository Structure",
        f"## Local Setup",
        f"## Deployment",
        f"## Demo Workflow",
        f"## Future Enhancements",
        f"\nUse the following information to populate the sections:",
        f"Project Name: {repo_name}",
        f"Full GitHub Name: {full_name}",
        f"GitHub URL: {repo_url}",
        f"Primary Description: {description}",
        f"Main Language: {language}",
    ]

    if tags != "N/A":
        prompt_parts.append(f"Key Themes/Tags: {tags}")

    if github_repo_context:
        prompt_parts.append("\n--- Additional Repository Context (integrate this information) ---")
        if github_repo_context.get("readme") and github_repo_context["readme"] != "No README.md found.":
            prompt_parts.append(f"Existing README content (for enrichment/reference, do not simply copy): {github_repo_context['readme']}")
        if github_repo_context.get("tech_stack"):
            prompt_parts.append(f"Detected Technologies from codebase: {', '.join(github_repo_context['tech_stack'])}")
        if github_repo_context.get("features"):
            prompt_parts.append(f"Inferred Features/Capabilities from codebase: {', '.join(github_repo_context['features'])}")
        if github_repo_context.get("files"):
            prompt_parts.append(f"Top-level files and directories in repository: {', '.join(github_repo_context['files'])}")
        prompt_parts.append("Deduce Architecture, Local Setup, Deployment, and Demo Workflow details from this context.")
    else:
        prompt_parts.append("\n--- IMPORTANT: No GitHub repository context was available. Generate the README using only the provided metadata. ---")

    full_prompt = "\n".join(prompt_parts)
    logging.debug(f"Sending prompt to LLM (first 500 chars):\n{full_prompt[:500]}...")

    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Gemini generation failed for {full_name}: {e}", exc_info=True)
        return ""

def publish_readme_to_github(
    owner: str, 
    repo_name: str, 
    readme_content: str, 
    github_token: str, 
    branch: str = "main", 
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Publishes the generated README.md content to GitHub using the GitHub REST API.
    Updates if it exists, creates if it doesn't.
    """
    full_github_repo = f"{owner}/{repo_name}"
    url = f"https://api.github.com/repos/{full_github_repo}/contents/README.md"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    commit_message = "docs: add project README"

    logging.debug(f"Attempting to publish README to {full_github_repo}/{branch} (dry_run={dry_run})")

    if dry_run:
        logging.info(f"DRY RUN: Would publish/update README for '{full_github_repo}' on branch '{branch}'.")
        return {"status": "DRY_RUN_SUCCESS"}

    sha = None
    try:
        # Check if README.md exists to get its SHA
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            sha = file_data['sha']
            logging.debug(f"README.md exists for '{full_github_repo}', SHA: {sha}")
            commit_message = "docs: update project README"
        elif response.status_code == 404:
            logging.debug(f"README.md does not exist for '{full_github_repo}'. Will create.")
            commit_message = "docs: add project README"
        else:
            response.raise_for_status() # Raise for other HTTP errors

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to check existing README for '{full_github_repo}': {e}")
        return {"status": "FAILED", "reason": f"API check failed: {e}"}

    # Prepare content for PUT request
    encoded_content = base64.b64encode(readme_content.encode('utf-8')).decode('utf-8')
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status() # Raise for HTTP errors (4xx or 5xx)
        
        action = "updated" if sha else "created"
        logging.info(f"Successfully {action} README for '{full_github_repo}' on branch '{branch}'.")
        return {"status": "SUCCESS", "action": action}

    except requests.exceptions.HTTPError as e:
        error_details = e.response.json().get('message', str(e))
        logging.error(f"Failed to publish README for '{full_github_repo}': HTTPError {e.response.status_code} - {error_details}")
        return {"status": "FAILED", "reason": f"HTTPError {e.response.status_code}: {error_details}"}
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to publish README for '{full_github_repo}': {e}")
        return {"status": "FAILED", "reason": f"API PUT failed: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred during publishing for '{full_github_repo}': {e}", exc_info=True)
        return {"status": "FAILED", "reason": f"Unexpected error: {type(e).__name__} - {e}"}

def main():
    parser = argparse.ArgumentParser(description="Generate and optionally publish README drafts for GitHub repositories using Gemini.")
    parser.add_argument("--repo", type=str, help="Generate/publish README for a specific repo by its full name (e.g., owner/repo).")
    parser.add_argument("--all", action="store_true", help="Generate/publish READMEs for all relevant repos in config/repos.yaml.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing local generated READMEs.")
    parser.add_argument("--limit", type=int, default=0, help="Limit the number of repositories to process when --all is used.")
    parser.add_argument("--missing-only", action="store_true", 
                        help="Generate READMEs only for repos with 'No README found' in description or readme_available=false/missing.")
    parser.add_argument("--publish", action="store_true", help="Publish the generated README.md directly to GitHub.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run for publishing, showing what would happen without making changes.")
    parser.add_argument("--branch", type=str, default="main", help="GitHub branch to publish to (default: main).")
    parser.add_argument("--yes", action="store_true", help="Confirm bulk publish without prompt (required for --all --publish).")
    args = parser.parse_args()

    if not args.repo and not args.all:
        parser.error("Please specify either --repo <full_name> or --all.")

    repos_config_path = Path("config/repos.yaml")
    if not repos_config_path.exists():
        logging.error(f"Error: {repos_config_path} not found. Please ensure it exists.")
        sys.exit(1)

    try:
        with open(repos_config_path, "r") as f:
            repos_data = yaml.safe_load(f)
        all_repos = repos_data.get("repos", [])
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {repos_config_path}: {e}")
        sys.exit(1)

    # Validate arguments
    if args.publish and args.dry_run:
        parser.error("Cannot use --publish and --dry-run simultaneously.")
    if args.all and args.publish and not args.yes:
        parser.error("--all --publish requires --yes to confirm bulk publishing.")
    if args.publish and not os.environ.get("GITHUB_TOKEN"):
        parser.error("--publish requires GITHUB_TOKEN environment variable to be set in .env.local.")

    # Initialize report
    report = {
        "generated_locally": [],
        "skipped_local": [],
        "published_created": [],
        "published_updated": [],
        "failed": [],
        "summary": {
            "generated_locally_count": 0, 
            "skipped_local_count": 0, 
            "published_created_count": 0,
            "published_updated_count": 0,
            "failed_count": 0
        }
    }
    report_file_path = Path("generated_readmes") / "report.json"
    report_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists

    repos_to_process = []
    if args.repo:
        found = False
        for r in all_repos:
            if r.get("full_name") == args.repo:
                repos_to_process.append(r)
                found = True
                break
        if not found:
            logging.error(f"Repository '{args.repo}' not found in {repos_config_path}.")
            sys.exit(1)
    elif args.all:
        repos_to_process = all_repos
        if args.missing_only:
            initial_count = len(repos_to_process)
            repos_to_process = [
                r for r in repos_to_process if 
                ("No README found" in r.get("description", "") or 
                 r.get("readme_available", True) == False or # If missing, assume True until fetched
                 r.get("readme_available") is None)
            ]
            logging.info(f"Filtering for missing READMEs: {len(repos_to_process)} out of {initial_count} repos will be processed.")

    if args.limit > 0:
        repos_to_process = repos_to_process[:args.limit]
        logging.info(f"Limiting processing to {args.limit} repositories.")

    for repo_metadata in repos_to_process:
        full_name = repo_metadata.get("full_name")
        repo_url = repo_metadata.get("repo_url")
        if not full_name or not repo_url:
            logging.warning(f"Skipping repo with missing full_name or repo_url: {repo_metadata.get('name', 'Unknown')}")
            report["skipped_local"].append({"full_name": full_name, "reason": "Missing full_name or repo_url"})
            report["summary"]["skipped_count"] += 1
            continue

        owner, name = full_name.split('/')
        output_dir = Path("generated_readmes") / owner / name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "README.md"

        # Check if README needs generation based on --force and existence
        if output_file.exists() and not args.force:
            logging.info(f"SKIP existing: README for '{full_name}' already exists at '{output_file}' (use --force to overwrite).")
            report["skipped_local"].append({"full_name": full_name, "reason": "README exists, --force not used"})
            report["summary"]["skipped_count"] += 1
            continue
        
        logging.info(f"Processing README for '{full_name}'...")

        # Get GitHub token safely (already checked if --publish is true)
        github_token = os.environ.get("GITHUB_TOKEN") if args.publish else None

        # Try to extract owner and repo name from full_name for GitHub API
        owner_name_match = re.match(r"([^/]+)/([^/]+)", full_name)
        if not owner_name_match:
            logging.error(f"Invalid full_name format '{full_name}'. Skipping.")
            report["failed"].append({"full_name": full_name, "reason": "Invalid full_name format"})
            report["summary"]["failed_count"] += 1
            continue
        owner, repo_name = owner_name_match.groups()


        github_repo_context = None
        if github_reader_agent: # Only attempt if agent was loaded successfully
            try:
                github_repo_context = github_reader_agent(repo_url)
                # Check for error from github_reader_agent itself
                if "Error" in github_repo_context.get("name", ""):
                    logging.warning(f"Could not fetch GitHub repo context for {full_name}: {github_repo_context.get('description', '')}. Generating README from metadata only.")
                    github_repo_context = None
            except Exception as e:
                logging.warning(f"Failed to get GitHub repo context for {full_name}: {e}. Generating README from metadata only.", exc_info=True)
                github_repo_context = None
        else:
            logging.info(f"GitHub reader agent not available. Generating README for {full_name} from metadata only.")
        
        readme_content = ""
        retries = 3
        for i in range(retries):
            try:
                readme_content = generate_readme_content(repo_metadata, github_repo_context)
                if readme_content:
                    break # Success, exit retry loop
            except Exception as e:
                logging.warning(f"Gemini generation attempt {i+1}/{retries} failed for '{full_name}': {e}. Retrying in 5 seconds...")
                time.sleep(5) # Wait before retrying
        
        if readme_content:
            # 1. Save locally
            try:
                with open(output_file, "w") as f:
                    f.write(readme_content)
                logging.info(f"Generated local README for '{full_name}' at '{output_file}'.")
                report["generated_locally"].append({"full_name": full_name, "path": str(output_file)})
                report["summary"]["generated_locally_count"] += 1
            except Exception as e:
                logging.error(f"Failed to save local README for '{full_name}' to '{output_file}': {e}", exc_info=True)
                report["failed"].append({"full_name": full_name, "reason": f"Failed to save local file: {e}"})
                report["summary"]["failed_count"] += 1
                # If local save fails, don't attempt to publish
                continue 

            # 2. Optionally publish to GitHub
            if args.publish:
                publish_result = publish_readme_to_github(
                    owner, repo_name, readme_content, github_token, args.branch, args.dry_run
                )
                if publish_result["status"] == "SUCCESS":
                    if publish_result["action"] == "created":
                        report["published_created"].append({"full_name": full_name, "path": str(output_file)})
                        report["summary"]["published_created_count"] += 1
                    elif publish_result["action"] == "updated":
                        report["published_updated"].append({"full_name": full_name, "path": str(output_file)})
                        report["summary"]["published_updated_count"] += 1
                elif publish_result["status"] == "DRY_RUN_SUCCESS":
                    logging.info(f"DRY RUN: README for '{full_name}' would have been published.")
                else: # FAILED
                    report["failed"].append({"full_name": full_name, "reason": f"GitHub publish failed: {publish_result.get('reason', 'Unknown error')}"})
                    report["summary"]["failed_count"] += 1
        else:
            logging.error(f"Failed to generate content for README for '{full_name}' after {retries} attempts.")
            report["failed"].append({"full_name": full_name, "reason": "Failed to generate content from Gemini"})
            report["summary"]["failed_count"] += 1

    # Save final report
    with open(report_file_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n--- README Generation Report ---")
    print(f"Locally Generated: {report['summary']['generated_locally_count']}")
    print(f"Locally Skipped (exists): {report['summary']['skipped_local_count']}")
    print(f"Published (Created on GitHub): {report['summary']['published_created_count']}")
    print(f"Published (Updated on GitHub): {report['summary']['published_updated_count']}")
    print(f"Total Failed: {report['summary']['failed_count']}")
    print(f"Full report saved to: {report_file_path}")

if __name__ == "__main__":
    main()
