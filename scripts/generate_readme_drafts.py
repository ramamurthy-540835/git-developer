import os
import argparse
import logging
import yaml
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure google.generativeai is imported, potentially using a shared LLM agent later
try:
    import google.generativeai as genai
except ImportError:
    logging.error("google-generativeai not found. Please install it: pip install google-generativeai")
    exit(1)

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
    Generates a README markdown content using Gemini based on repository metadata and context.
    """
    repo_name = repo_metadata.get("name", "Unnamed Project").replace('-', ' ').replace('_', ' ').title()
    full_name = repo_metadata.get("full_name", "owner/repo")
    description = repo_metadata.get("description", "A project without a specific description.")
    repo_url = repo_metadata.get("repo_url", "N/A")
    language = repo_metadata.get("language", "N/A")
    tags = ", ".join(repo_metadata.get("tags", [])) if repo_metadata.get("tags") else "N/A"

    prompt_parts = [
        f"You are an expert technical writer and developer advocate. Your task is to generate a professional, comprehensive, and engaging README.md in markdown format for a GitHub repository.",
        f"The README should clearly explain the project's purpose, key features, technical stack, architecture, demo workflow, how to run it locally, and deployment notes.",
        f"Project Title: {repo_name}",
        f"Repository Full Name: {full_name}",
        f"Repository URL: {repo_url}",
        f"Primary Description: {description}",
        f"Primary Language: {language}",
    ]

    if tags != "N/A":
        prompt_parts.append(f"Key Themes/Tags: {tags}")

    if github_repo_context:
        prompt_parts.append("\n\n--- Additional GitHub Repository Context ---\n")
        if github_repo_context.get("readme") and github_repo_context["readme"] != "No README.md found.":
            prompt_parts.append(f"Existing README content (if available for enrichment): {github_repo_context['readme']}")
        if github_repo_context.get("tech_stack"):
            prompt_parts.append(f"Detected Technical Stack from codebase: {', '.join(github_repo_context['tech_stack'])}")
        if github_repo_context.get("features"):
            prompt_parts.append(f"Inferred Features/Capabilities from codebase: {', '.join(github_repo_context['features'])}")
        if github_repo_context.get("files"):
            prompt_parts.append(f"Top-level files/folders in repository: {', '.join(github_repo_context['files'])}")
        
        prompt_parts.append("\n\nBased on this context, deduce the project's architecture, expected UI flows, how to run it, and deployment patterns.")
    
    prompt_parts.append("\n\nGenerate the README following these sections in markdown. Provide concrete examples where appropriate:")
    prompt_parts.append("- # Project Title (use the project name, e.g., # Value-Based Care Dashboard)")
    prompt_parts.append("- ## Overview (briefly explain what it is)")
    prompt_parts.append("- ## The Business Problem (what challenge does it solve)")
    prompt_parts.append("- ## Key Capabilities / Features (list and briefly describe main features)")
    prompt_parts.append("- ## Tech Stack (list core technologies)")
    prompt_parts.append("- ## Architecture (high-level design, main components, how they interact)")
    prompt_parts.append("- ## Demo Workflow (step-by-step example of how to use it)")
    prompt_parts.append("- ## Getting Started (how to run it locally, prerequisites)")
    prompt_parts.append("- ## Deployment (brief notes on how to deploy)")
    prompt_parts.append("- ## Future Enhancements (potential next steps)")
    prompt_parts.append("\nDo not include any conversational text outside of the README markdown itself. Ensure all sections are present.")


    full_prompt = "\n".join(prompt_parts)
    logging.debug(f"Sending prompt to LLM:\n{full_prompt}")

    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating README for {full_name} with Gemini: {e}")
        return ""

def main():
    parser = argparse.ArgumentParser(description="Generate README drafts for GitHub repositories using Gemini.")
    parser.add_argument("--repo", type=str, help="Generate README for a specific repo by its full name (e.g., owner/repo).")
    parser.add_argument("--all", action="store_true", help="Generate READMEs for all relevant repos in config/repos.yaml.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated READMEs.")
    args = parser.parse_args()

    if not args.repo and not args.all:
        parser.error("Please specify either --repo <full_name> or --all.")

    repos_config_path = Path("config/repos.yaml")
    if not repos_config_path.exists():
        logging.error(f"Error: {repos_config_path} not found. Please ensure it exists.")
        exit(1)

    try:
        with open(repos_config_path, "r") as f:
            repos_data = yaml.safe_load(f)
        all_repos = repos_data.get("repos", [])
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {repos_config_path}: {e}")
        exit(1)

    generated_count = 0
    skipped_count = 0
    failed_count = 0

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
            exit(1)
    elif args.all:
        repos_to_process = all_repos

    for repo_metadata in repos_to_process:
        full_name = repo_metadata.get("full_name")
        repo_url = repo_metadata.get("repo_url")
        if not full_name or not repo_url:
            logging.warning(f"Skipping repo with missing full_name or repo_url: {repo_metadata.get('name', 'Unknown')}")
            skipped_count += 1
            continue

        owner, name = full_name.split('/')
        output_dir = Path("generated_readmes") / owner / name
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "README.md"

        # Check if README needs generation
        should_generate = False
        if args.force:
            should_generate = True
        elif not output_file.exists():
            should_generate = True
        elif (repo_metadata.get("description") and "No README found" in repo_metadata["description"]) or \
             (repo_metadata.get("readme_available") == False):
            should_generate = True
        elif repo_metadata.get("readme_available") is None: # If field is missing, assume it needs update
            should_generate = True
        
        if not should_generate:
            logging.info(f"Skipping '{full_name}': README already exists at '{output_file}' (use --force to overwrite).")
            skipped_count += 1
            continue

        logging.info(f"Generating README for '{full_name}'...")

        # Optional: Fetch GitHub repo context for richer README generation
        # This part assumes github_reader_agent can be called from here.
        # If github_reader_agent is an async function, you'd need an asyncio loop.
        # For simplicity, if github_reader_agent is synchronous, you can call it directly.
        # For now, let's assume get_repo_context is synchronous as defined in the chat history.
        github_repo_context = None
        try:
            from agents.github_reader_agent import get_repo_context
            github_repo_context = get_repo_context(repo_url)
            if "Error" in github_repo_context.get("name", ""):
                logging.warning(f"Could not fetch GitHub repo context for {full_name}: {github_repo_context.get('description', '')}. Generating README from metadata only.")
                github_repo_context = None # Reset to ensure it's not used if there's an error
        except ImportError:
            logging.warning("agents.github_reader_agent not found. Skipping dynamic repo context enrichment.")
        except Exception as e:
            logging.warning(f"Failed to get GitHub repo context for {full_name}: {e}. Generating README from metadata only.")
            github_repo_context = None


        readme_content = generate_readme_content(repo_metadata, github_repo_context)

        if readme_content:
            try:
                with open(output_file, "w") as f:
                    f.write(readme_content)
                logging.info(f"Successfully generated README for '{full_name}' at '{output_file}'.")
                generated_count += 1
            except Exception as e:
                logging.error(f"Failed to save README for '{full_name}' to '{output_file}': {e}")
                failed_count += 1
        else:
            logging.error(f"Failed to generate content for README for '{full_name}'.")
            failed_count += 1

    print("\n--- README Generation Report ---")
    print(f"Generated: {generated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Failed: {failed_count}")

if __name__ == "__main__":
    main()
