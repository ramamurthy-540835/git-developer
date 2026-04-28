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
        f"## Tech Stack",
        f"## Repository Structure",
        f"## Local Setup",
        f"## Deployment",
        f"## Demo Workflow",
        f"## Future Enhancements",
        f"\nIMPORTANT: The 'Architecture' section will be added programmatically with a Mermaid diagram or a bullet list. Do not generate it here.",
        f"\nUse the following information to populate the sections (excluding Architecture):",
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
        generated_content = response.text.strip()
        return generated_content
    except Exception as e:
        logging.error(f"Gemini generation failed for {full_name}: {e}", exc_info=True)
        return ""

def detect_repo_archetype(repo_metadata: Dict[str, Any], github_repo_context: Optional[Dict[str, Any]]) -> str:
    """
    Detects the repository archetype based on metadata and GitHub context.
    """
    repo_name = repo_metadata.get("name", "").lower()
    description = repo_metadata.get("description", "").lower()
    language = repo_metadata.get("language", "").lower()
    tech_stack = [t.lower() for t in github_repo_context.get("tech_stack", [])] if github_repo_context else []
    features = [f.lower() for f in github_repo_context.get("features", [])] if github_repo_context else []
    files = [f.lower() for f in github_repo_context.get("files", [])] if github_repo_context else []

    # Prioritize specific platforms/apps
    if "weather" in repo_name or "weather" in description or "weather" in features:
        return "weather_platform"
    if "healthcare" in repo_name or "healthcare" in description or "care" in features:
        return "healthcare_platform"
    if "agent" in repo_name or "agent" in description or "llm" in tech_stack or "gemini" in tech_stack or "ai" in features:
        return "agent_platform"
    if "data" in repo_name or "data" in description or "data" in tech_stack or "analytics" in features:
        return "data_platform"

    # Then general types
    if "nextjs" in tech_stack or language == "typescript" or "frontend" in files or "app/page.js" in files:
        return "nextjs_app"
    if language == "python" or "flask" in tech_stack or "django" in tech_stack or "backend" in files:
        return "python_backend"
    
    return "generic_app"


def build_architecture_steps(archetype: str, repo_metadata: Dict[str, Any], github_repo_context: Optional[Dict[str, Any]]) -> List[str]:
    """
    Builds a list of 5 to 7 architecture steps based on the detected archetype.
    """
    repo_name_title = repo_metadata.get("name", "Application").replace('-', ' ').replace('_', ' ').title()
    description = repo_metadata.get("description", "")

    base_steps = []

    if archetype == "nextjs_app":
        base_steps = [
            f"User opens the {repo_name_title} web application",
            "Next.js frontend renders pages and components",
            "API routes handle application requests",
            "Backend services process business logic",
            "External APIs or data stores provide data",
            "UI displays generated insights and actions"
        ]
    elif archetype == "python_backend":
        base_steps = [
            "Client sends API request",
            f"Load balancer/API Gateway routes request to {repo_name_title} backend",
            "Python backend processes request with business logic",
            "Database or external services are queried",
            "Backend generates and returns API response"
        ]
    elif archetype == "agent_platform":
        base_steps = [
            "User submits task or prompt",
            f"Frontend sends request to {repo_name_title} orchestration API",
            "Agent orchestrator plans the workflow",
            "Specialized agents execute tools and business logic",
            "LLM service generates structured output",
            "Results are stored, reviewed, and displayed to the user"
        ]
    elif archetype == "data_platform":
        base_steps = [
            "Data sources ingest raw data",
            f"Data processing pipelines transform data for {repo_name_title}",
            "Data is stored in warehouses/lakes",
            "Analytics layer queries and processes data",
            "Reporting/Visualization tools display insights",
            "Users consume insights for decision making"
        ]
    elif archetype == "healthcare_platform":
        base_steps = [
            f"Care team opens {repo_name_title} dashboard",
            "Frontend shows patient cohorts and workflow views",
            "Backend APIs load clinical and operational data",
            "Analytics layer calculates risk, care gaps, and quality measures",
            "AI agents generate recommendations and next actions",
            "Users review insights and trigger care management workflows"
        ]
    elif archetype == "weather_platform":
        base_steps = [
            f"User opens {repo_name_title} dashboard",
            "Next.js frontend renders forecast views and maps",
            "API routes request weather and climate data",
            "Forecast engine processes city and model inputs",
            "AI insight layer generates alerts and decision briefs",
            "Dashboard displays forecasts, risks, and export options"
        ]
    else: # generic_app
        base_steps = [
            "User interacts with the application interface",
            "Frontend sends requests to the backend",
            "Backend processes requests and applies business logic",
            "Data is retrieved from or stored in the database",
            "External services or APIs are integrated (if applicable)",
            "Results are returned and displayed to the user"
        ]

    # Dynamically add an extra step if there's a strong AI/ML presence and < 7 steps
    if len(base_steps) < 7 and ("ai" in description or "machine learning" in description or "gemini" in tech_stack or "llm" in tech_stack):
        base_steps.insert(len(base_steps) - 1, "AI/ML models process data and generate insights")
        
    return base_steps[:7] # Ensure max 7 steps

def steps_to_mermaid(steps: List[str]) -> str:
    """
    Converts a list of architecture steps (5-7) into a Mermaid flowchart TD string.
    Quotes all labels and strips unsafe characters.
    """
    if not steps or not (5 <= len(steps) <= 7):
        logging.warning(f"Invalid number of steps for Mermaid diagram: {len(steps)}. Expected 5-7.")
        return ""

    diagram_lines = ["flowchart TD"]
    
    # Generate node IDs (A, B, C, ...)
    node_ids = [chr(ord('A') + i) for i in range(len(steps))]

    # Define nodes with quoted labels
    for i, step in enumerate(steps):
        # Sanitize label: replace double quotes with single, remove newlines, trim whitespace.
        sanitized_step = step.replace('"', "'").replace('\n', ' ').strip()
        diagram_lines.append(f"  {node_ids[i]}[\"{sanitized_step}\"]")

    # Define connections
    for i in range(len(steps) - 1):
        diagram_lines.append(f"  {node_ids[i]} --> {node_ids[i+1]}")
    
    return "\n".join(diagram_lines)

def generate_architecture_html(mermaid_content: str, title: str) -> str:
    """
    Generates an HTML file content to preview a Mermaid diagram.
    """
    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - Architecture Diagram</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .mermaid {{ width: 100%; height: auto; }}
    </style>
</head>
<body>
    <h1>{title} Architecture Diagram</h1>
    <div class="mermaid">
{mermaid_content}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>"""
    return html_template

def publish_file_to_github(
    owner: str,
    repo_name: str,
    file_path_in_repo: Path, # e.g., README.md, docs/architecture.mmd
    file_content: str,
    github_token: str,
    branch: str = "main",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Publishes the given file content to GitHub using the GitHub REST API.
    Updates if it exists, creates if it doesn't.
    """
    full_github_repo = f"{owner}/{repo_name}"
    file_path_str = str(file_path_in_repo)
    url = f"https://api.github.com/repos/{full_github_repo}/contents/{file_path_str}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    commit_message_action = "add" if file_path_str == "README.md" else "create"
    commit_message_type = "docs" if file_path_str.startswith("docs/") or file_path_str == "README.md" else "feat" # Default
    commit_message = f"{commit_message_type}: {commit_message_action} {file_path_str}"

    logging.debug(f"Attempting to publish {file_path_str} to {full_github_repo}/{branch} (dry_run={dry_run})")

    if dry_run:
        logging.info(f"DRY RUN: Would publish/update '{file_path_str}' for '{full_github_repo}' on branch '{branch}'.")
        return {"status": "DRY_RUN_SUCCESS", "file_path": file_path_str}

    sha = None
    action_performed = "created" # Default to created
    
    try:
        # Check if file exists to get its SHA
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            file_data = response.json()
            sha = file_data['sha']
            logging.debug(f"'{file_path_str}' exists for '{full_github_repo}', SHA: {sha}")
            commit_message_action = "update"
            commit_message = f"{commit_message_type}: {commit_message_action} {file_path_str}"
            action_performed = "updated"
        elif response.status_code == 404:
            logging.debug(f"'{file_path_str}' does not exist for '{full_github_repo}'. Will create.")
            # commit_message already set for 'add' or 'create'
        else:
            response.raise_for_status() # Raise for other HTTP errors

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to check existing '{file_path_str}' for '{full_github_repo}': {e}")
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"API check failed: {e}"}
    except Exception as e: # Catch any other unexpected errors during the GET request
        logging.error(f"An unexpected error occurred during check for existing '{file_path_str}' for '{full_github_repo}': {e}", exc_info=True)
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"Unexpected error during GET check: {type(e).__name__} - {e}"}

    # Prepare content for PUT request
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
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
        
        logging.info(f"Successfully {action_performed} '{file_path_str}' for '{full_github_repo}' on branch '{branch}'.")
        return {"status": "SUCCESS", "action": action_performed, "file_path": file_path_str}

    except requests.exceptions.HTTPError as e:
        error_details = e.response.json().get('message', str(e))
        logging.error(f"Failed to publish '{file_path_str}' for '{full_github_repo}': HTTPError {e.response.status_code} - {error_details}")
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"HTTPError {e.response.status_code}: {error_details}"}
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to publish '{file_path_str}' for '{full_github_repo}': {e}")
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"API PUT failed: {e}"}
    except Exception as e:
        logging.error(f"An unexpected error occurred during publishing '{file_path_str}' for '{full_github_repo}': {e}", exc_info=True)
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"Unexpected error: {type(e).__name__} - {e}"}

def main():
    parser = argparse.ArgumentParser(description="Generate and optionally publish README drafts and architecture diagrams for GitHub repositories using Gemini.")
    parser.add_argument("--repo", type=str, help="Generate/publish for a specific repo by its full name (e.g., owner/repo).")
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
    # --dry-run can be used with --publish to simulate the action
    if args.all and args.publish and not args.yes and not args.dry_run:
        parser.error("--all --publish requires --yes to confirm bulk publishing (unless --dry-run is used).")
    
    # GITHUB_TOKEN is only required for actual publishing, not dry runs
    if args.publish and not args.dry_run and not os.environ.get("GITHUB_TOKEN"):
        parser.error("--publish (without --dry-run) requires GITHUB_TOKEN environment variable to be set in .env.local.")

    # Initialize report
    report = {
        "generated_locally": [],
        "skipped_local": [],
        "published_files": [], # To store all published files (readme, mmd, html)
        "failed": [],
        "summary": {
            "generated_locally_count": 0, 
            "skipped_local_count": 0, 
            "published_count": 0, # Total published files (any type)
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
            report["summary"]["skipped_local_count"] += 1
            continue

        owner, name = full_name.split('/')
        output_dir = Path("generated_readmes") / owner / name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "README.md"

        logging.info(f"Processing '{full_name}'...")

        # Derive owner and repo_name for file paths
        owner_name_match = re.match(r"([^/]+)/([^/]+)", full_name)
        if not owner_name_match:
            logging.error(f"Invalid full_name format '{full_name}'. Skipping.")
            report["failed"].append({"full_name": full_name, "reason": "Invalid full_name format"})
            report["summary"]["failed_count"] += 1
            continue
        owner, repo_name = owner_name_match.groups()

        output_repo_dir = Path("generated_readmes") / owner / repo_name
        output_repo_dir.mkdir(parents=True, exist_ok=True)

        readme_output_file = output_repo_dir / "README.md"
        docs_dir = output_repo_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        mermaid_output_file = docs_dir / "architecture.mmd"
        html_output_file = docs_dir / "architecture.html"

        # Initialize content variables
        readme_content = ""
        mermaid_content = ""
        html_content = ""
        architecture_flow_bullet_list = "" # Fallback for README

        # --- Phase 1: Determine if README content needs generation or uses existing ---
        generated_new_readme_locally = False
        if readme_output_file.exists() and not args.force:
            if args.publish:
                # If local README exists, not forcing, but publishing, read existing local content
                try:
                    with open(readme_output_file, "r") as f:
                        readme_content = f.read()
                    logging.info(f"SKIP README generation: Using existing local README for '{full_name}' for publishing.")
                    # Also read existing architecture files if they exist for publishing
                    if mermaid_output_file.exists():
                        with open(mermaid_output_file, "r") as f:
                            mermaid_content = f.read()
                    if html_output_file.exists():
                        with open(html_output_file, "r") as f:
                            html_content = f.read()

                    report["skipped_local"].append({"full_name": full_name, "file": "README.md", "reason": "Using existing local for publish"})
                    report["summary"]["skipped_local_count"] += 1
                except Exception as e:
                    logging.error(f"Failed to read existing local README/architecture files for '{full_name}': {e}", exc_info=True)
                    report["failed"].append({"full_name": full_name, "reason": f"Failed to read existing local files: {e}"})
                    report["summary"]["failed_count"] += 1
                    continue # Cannot proceed without content
            else:
                # If local exists, not forcing, and not publishing, skip completely
                logging.info(f"SKIP existing: README for '{full_name}' already exists at '{readme_output_file}' (use --force to overwrite or --publish to publish existing).")
                report["skipped_local"].append({"full_name": full_name, "file": "README.md", "reason": "README exists, skipping"})
                report["summary"]["skipped_local_count"] += 1
                continue # Skip to next repo
        
        # --- Phase 2: Generate new content if not using existing local ---
        if not readme_content: # Means we need to generate README and architecture diagrams
            logging.info(f"Generating new README and architecture files for '{full_name}'.")

            # Get GitHub token safely for agent
            github_token_for_agent = os.environ.get("GITHUB_TOKEN") 
            if not github_token_for_agent and github_reader_agent:
                 logging.warning(f"GITHUB_TOKEN not set for '{full_name}'. GitHub reader agent may not function correctly.")
            
            github_repo_context = None
            if github_reader_agent: # Only attempt if agent was loaded successfully
                try:
                    github_repo_context = github_reader_agent(repo_url)
                    if "Error" in github_repo_context.get("name", ""):
                        logging.warning(f"Could not fetch GitHub repo context for {full_name}: {github_repo_context.get('description', '')}. Generating content from metadata only.")
                        github_repo_context = None
                except Exception as e:
                    logging.warning(f"Failed to get GitHub repo context for {full_name}: {e}. Generating content from metadata only.", exc_info=True)
                    github_repo_context = None
            else:
                logging.info(f"GitHub reader agent not available. Generating content for {full_name} from metadata only.")
            
            # --- Generate README.md base content ---
            retries = 3
            for i in range(retries):
                try:
                    readme_content = generate_readme_content(repo_metadata, github_repo_context)
                    if readme_content:
                        break
                except Exception as e:
                    logging.warning(f"Gemini README generation attempt {i+1}/{retries} failed for '{full_name}': {e}. Retrying in 5 seconds...")
                    time.sleep(5) # Wait before retrying
            
            if not readme_content:
                logging.error(f"Failed to generate base README content for '{full_name}' after {retries} attempts.")
                report["failed"].append({"full_name": full_name, "file": "README.md", "reason": "Failed to generate content from Gemini"})
                report["summary"]["failed_count"] += 1
                continue # Cannot proceed without README content

            # --- Determine Architecture and Generate Diagram components ---
            archetype = detect_repo_archetype(repo_metadata, github_repo_context)
            logging.info(f"Detected archetype for '{full_name}': {archetype}")
            
            architecture_steps = build_architecture_steps(archetype, repo_metadata, github_repo_context)

            if architecture_steps:
                mermaid_content = steps_to_mermaid(architecture_steps)
                if mermaid_content:
                    html_content = generate_architecture_html(mermaid_content, repo_name)
                    logging.info(f"Generated architecture diagram for '{full_name}'.")
                else:
                    logging.warning(f"Mermaid content generation failed for '{full_name}' with {len(architecture_steps)} steps. Falling back to bullet list.")
                    architecture_flow_bullet_list = "\n" + "\n".join([f"* {step}" for step in architecture_steps]) + "\n"
            else:
                logging.warning(f"Failed to build architecture flow steps for '{full_name}'. Falling back to simple placeholder.")
                architecture_flow_bullet_list = "\n* Architecture flow steps could not be generated. Please review the project manually.\n"
            
            # --- Insert Architecture section into README content ---
            architecture_section_markdown = "\n## Architecture\n\n"
            if mermaid_content:
                architecture_section_markdown += "```mermaid\n"
                architecture_section_markdown += mermaid_content
                architecture_section_markdown += "\n```\n"
                architecture_section_markdown += f"\nFor a standalone preview, see [docs/architecture.html](docs/architecture.html).\n"
            else:
                architecture_section_markdown += architecture_flow_bullet_list

            # Find a suitable place to insert, e.g., before 'Tech Stack' or at the end
            # We defined the prompt *not* to include "## Architecture", so we just append it.
            readme_content += architecture_section_markdown
            
            generated_new_readme_locally = True # Mark as newly generated

            # --- Save all generated content locally ---
            try:
                with open(readme_output_file, "w") as f:
                    f.write(readme_content)
                logging.info(f"Generated local README for '{full_name}' at '{readme_output_file}'.")
                report["generated_locally"].append({"full_name": full_name, "file": "README.md", "path": str(readme_output_file)})
                report["summary"]["generated_locally_count"] += 1

                if mermaid_content:
                    with open(mermaid_output_file, "w") as f:
                        f.write(mermaid_content)
                    logging.info(f"Generated local Mermaid diagram for '{full_name}' at '{mermaid_output_file}'.")
                    report["generated_locally"].append({"full_name": full_name, "file": "architecture.mmd", "path": str(mermaid_output_file)})
                    report["summary"]["generated_locally_count"] += 1

                    with open(html_output_file, "w") as f:
                        f.write(html_content)
                    logging.info(f"Generated local HTML preview for '{full_name}' at '{html_output_file}'.")
                    report["generated_locally"].append({"full_name": full_name, "file": "architecture.html", "path": str(html_output_file)})
                    report["summary"]["generated_locally_count"] += 1
            except Exception as e:
                logging.error(f"Failed to save local files for '{full_name}': {e}", exc_info=True)
                report["failed"].append({"full_name": full_name, "reason": f"Failed to save local files: {e}"})
                report["summary"]["failed_count"] += 1
                continue # If local save fails, don't attempt to publish

        # --- Phase 3: Optionally publish to GitHub ---
        if args.publish: 
            github_token = os.environ.get("GITHUB_TOKEN") # Get GitHub token specifically for publishing

            files_to_publish = []
            if readme_content:
                files_to_publish.append({"path": readme_output_file, "content": readme_content})
            if mermaid_content:
                files_to_publish.append({"path": mermaid_output_file, "content": mermaid_content})
            if html_content:
                files_to_publish.append({"path": html_output_file, "content": html_content})

            for file_info in files_to_publish:
                file_path = file_info["path"]
                file_content = file_info["content"]

                publish_result = publish_file_to_github(
                    owner, repo_name, file_path.relative_to(output_repo_dir), file_content, github_token, args.branch, args.dry_run
                )
                if publish_result["status"] == "SUCCESS":
                    report["published_files"].append({
                        "full_name": full_name, 
                        "file": publish_result["file_path"], 
                        "action": publish_result["action"]
                    })
                    report["summary"]["published_count"] += 1
                elif publish_result["status"] == "DRY_RUN_SUCCESS":
                    logging.info(f"DRY RUN: '{publish_result['file_path']}' for '{full_name}' would have been published.")
                else: # FAILED
                    report["failed"].append({
                        "full_name": full_name, 
                        "file": publish_result["file_path"], 
                        "reason": f"GitHub publish failed: {publish_result.get('reason', 'Unknown error')}"
                    })
                    report["summary"]["failed_count"] += 1

    # Save final report
    with open(report_file_path, "w") as f:
        json.dump(report, f, indent=2)

    print("\n--- Generation and Publish Report ---")
    print(f"Locally Generated Files: {report['summary']['generated_locally_count']}")
    print(f"Locally Skipped Files (exists): {report['summary']['skipped_local_count']}")
    print(f"Published Files to GitHub: {report['summary']['published_count']}")
    print(f"Total Failed Operations: {report['summary']['failed_count']}")
    print(f"Full report saved to: {report_file_path}")

if __name__ == "__main__":
    main()
