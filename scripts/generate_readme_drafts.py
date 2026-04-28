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

def get_architecture_flow_steps_from_llm(repo_metadata: Dict[str, Any], github_repo_context: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Asks Gemini to generate a JSON list of architecture flow steps.
    """
    repo_name = repo_metadata.get("name", "Unnamed Project").replace('-', ' ').replace('_', ' ').title()
    description = repo_metadata.get("description", "A comprehensive project.")
    
    prompt_parts = [
        f"Generate ONLY a JSON object containing a list of strings, where each string is a concise step in the project's architecture flow. Limit the list to a maximum of 6 steps.",
        f"The JSON should be in the exact format: {{\"architecture_flow\": [\"step 1\", \"step 2\", ...]}}",
        f"Project Name: {repo_name}",
        f"Primary Description: {description}",
    ]
    
    if github_repo_context:
        prompt_parts.append("\n--- Additional Repository Context (integrate this information for architecture flow) ---")
        if github_repo_context.get("tech_stack"):
            prompt_parts.append(f"Detected Technologies from codebase: {', '.join(github_repo_context['tech_stack'])}")
        if github_repo_context.get("features"):
            prompt_parts.append(f"Inferred Features/Capabilities from codebase: {', '.join(github_repo_context['features'])}")
        if github_repo_context.get("files"):
            prompt_parts.append(f"Top-level files and directories in repository: {', '.join(github_repo_context['files'])}")
        prompt_parts.append("Deduce the architecture flow steps from this context.")
    else:
        prompt_parts.append("\n--- IMPORTANT: No GitHub repository context was available. Generate the architecture flow using only the provided metadata. ---")

    full_prompt = "\n".join(prompt_parts)
    logging.debug(f"Sending architecture flow prompt to LLM (first 500 chars):\n{full_prompt[:500]}...")

    try:
        response = model.generate_content(full_prompt)
        generated_json_str = response.text.strip()
        logging.debug(f"Raw architecture flow JSON from LLM: {generated_json_str}")
        # Attempt to parse, sometimes LLMs wrap JSON in markdown code blocks
        if generated_json_str.startswith("```json") and generated_json_str.endswith("```"):
            generated_json_str = generated_json_str[len("```json"):-len("```")].strip()

        data = json.loads(generated_json_str)
        if "architecture_flow" in data and isinstance(data["architecture_flow"], list):
            return data["architecture_flow"][:6] # Ensure max 6 steps
        else:
            logging.warning(f"LLM response for architecture flow did not contain 'architecture_flow' list or was malformed: {generated_json_str}")
            return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse architecture flow JSON from LLM: {e}. Raw response: {generated_json_str}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"Gemini generation failed for architecture flow: {e}", exc_info=True)
        return []

def steps_to_mermaid(steps: List[str]) -> str:
    """
    Converts a list of architecture steps into a Mermaid flowchart TD string.
    Quotes all labels and strips unsafe characters. Limits to max 6 steps.
    """
    if not steps:
        return ""

    diagram_lines = ["flowchart TD"]
    steps = steps[:6] # Ensure max 6 steps
    
    node_ids = [chr(ord('A') + i) for i in range(len(steps))]

    for i, step in enumerate(steps):
        # Sanitize label: replace double quotes with single, remove newlines, trim whitespace.
        # Ensure it's safe for a Mermaid quoted label.
        sanitized_step = step.replace('"', "'").replace('\n', ' ').strip()
        diagram_lines.append(f"  {node_ids[i]}[\"{sanitized_step}\"]")

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

            # --- Generate Architecture Diagram components ---
            architecture_steps = []
            for i in range(retries):
                try:
                    architecture_steps = get_architecture_flow_steps_from_llm(repo_metadata, github_repo_context)
                    if architecture_steps:
                        break
                except Exception as e:
                    logging.warning(f"Gemini architecture flow generation attempt {i+1}/{retries} failed for '{full_name}': {e}. Retrying in 5 seconds...")
                    time.sleep(5) # Wait before retrying
            
            if architecture_steps:
                mermaid_content = steps_to_mermaid(architecture_steps)
                if mermaid_content:
                    html_content = generate_architecture_html(mermaid_content, repo_name)
                    logging.info(f"Generated architecture diagram for '{full_name}'.")
                else:
                    logging.warning(f"Mermaid content generation failed for '{full_name}'. Falling back to bullet list.")
                    architecture_flow_bullet_list = "\n" + "\n".join([f"* {step}" for step in architecture_steps]) + "\n"
            else:
                logging.warning(f"Failed to generate architecture flow steps from Gemini for '{full_name}' after {retries} attempts. Falling back to simple placeholder.")
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
