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

from google import genai

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

# Load environment variables from .env.local
load_dotenv(dotenv_path='./.env.local')

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"

def create_genai_client():
    """
    Creates and returns a genai.Client instance, preferring an API key,
    then falling back to Vertex AI ADC.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if gemini_api_key:
        logging.info("Initializing genai client with API key.")
        return genai.Client(api_key=gemini_api_key)
    
    logging.info("API key not found, attempting to initialize genai client with Vertex AI ADC.")
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        location = os.getenv("VERTEX_AI_LOCATION") or os.getenv("GCP_REGION") or "us-central1"
        
        if not project_id:
            logging.error("GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID environment variable not set for Vertex AI.")
            sys.exit(1)
            
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
    except Exception as e:
        logging.error(f"Failed to initialize genai client with Vertex AI: {e}. Please ensure gcloud is configured or an API key is provided.")
        sys.exit(1)

client = create_genai_client()

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

    retries = 2
    for i in range(retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=full_prompt,
            )
            generated_content = response.text.strip()
            if generated_content:
                return generated_content
            else:
                raise ValueError("LLM returned empty content.")
        except Exception as e:
            logging.warning(f"Gemini README generation attempt {i+1}/{retries+1} failed for '{full_name}': {e}. Retrying in 5 seconds...")
            if i < retries:
                time.sleep(5) # Wait before retrying
            else:
                logging.error(f"Failed to generate content for README for '{full_name}' after {retries+1} attempts.")
                return ""
    return "" # Should not be reached if retries are exhausted and error is logged

def generate_diagram_plan(repo_metadata: Dict[str, Any], github_repo_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Asks Gemini to generate a structured JSON plan for an architecture diagram.
    Includes retry logic for JSON parsing failures.
    """
    repo_name = repo_metadata.get("name", "Unnamed Project").replace('-', ' ').replace('_', ' ').title()
    description = repo_metadata.get("description", "A comprehensive project.")
    language = repo_metadata.get("language", "Not specified")

    prompt_parts = [
        f"Analyze the following repository information and generate ONLY a JSON object representing an architecture diagram plan.",
        f"The JSON object must have the following structure and adhere to the rules below:",
        f"{{",
        f"  \"project_topic\": \"<A concise topic/summary of the project>\",",
        f"  \"architecture_style\": \"<frontend_backend_ai|data_pipeline|agent_workflow|dashboard_analytics|generic>\",",
        f"  \"nodes\": [",
        f"    {{\"id\": \"<NodeID>\", \"label\": \"<Descriptive Node Label (can use \\n for multiline)>\", \"layer\": \"<UI Layer|API Layer|Processing Layer|AI Layer|Data/Storage Layer>\"}}",
        f"    // ... 4 to 8 nodes total",
        f"  ],",
        f"  \"edges\": [",
        f"    {{\"from\": \"<SourceNodeID>\", \"to\": \"<TargetNodeID>\"}}",
        f"    // ... connections between nodes (no labels on edges)",
        f"  ],",
        f"  \"summary_bullets\": [",
        f"    \"<Bullet point summarizing an aspect of the architecture>\"",
        f"    // ... 2 to 4 summary bullets",
        f"  ]",
        f"}}",
        f"\nRules:",
        f"- The 'nodes' array must contain between 4 and 8 elements.",
        f"- Node 'label' values must be descriptive, complete, and incorporate the actions/data flow that would typically be on an edge. Use '\\n' for multiline text if needed for clarity.",
        f"- Node 'id' values must be unique single uppercase letters (e.g., \"A\", \"B\").",
        f"- Each node MUST have a 'layer' attribute, which must be one of: \"UI Layer\", \"API Layer\", \"Processing Layer\", \"AI Layer\", \"Data/Storage Layer\".",
        f"- Edge 'from' and 'to' IDs must refer to existing node IDs. Edge labels are NOT used.",
        f"- The diagram plan must accurately reflect the actual repo topic and core functionality.",
        f"- Use specific project terms when known (e.g., 'WeatherNext Dashboard', 'LinkedIn Generator', 'VBC Platform', 'Prompt Craft Engine', 'Agent Orchestrator').",
        f"- Do NOT include any raw Mermaid syntax in the JSON or any markdown formatting.",
        f"- Do NOT include any introductory or concluding remarks, just the JSON object.",
        f"\nProject Name: {repo_name}",
        f"Primary Description: {description}",
        f"Main Language: {language}",
    ]

    if github_repo_context:
        prompt_parts.append("\n--- Additional Repository Context (integrate this information) ---")
        if github_repo_context.get("readme") and github_repo_context["readme"] != "No README.md found.":
            # Provide first 500 chars of README to avoid excessively long prompts
            prompt_parts.append(f"First part of existing README content: {github_repo_context['readme'][:500]}...")
        if github_repo_context.get("tech_stack"):
            prompt_parts.append(f"Detected Technologies: {', '.join(github_repo_context['tech_stack'])}")
        if github_repo_context.get("features"):
            prompt_parts.append(f"Inferred Features: {', '.join(github_repo_context['features'])}")
        if github_repo_context.get("files"):
            prompt_parts.append(f"Top-level files and directories: {', '.join(github_repo_context['files'])}")
        prompt_parts.append("Use this context to inform the nodes, edges, and overall architecture style.")
    else:
        prompt_parts.append("\n--- IMPORTANT: No GitHub repository context was available. Generate the diagram plan using only the provided metadata. ---")

    full_prompt = "\n".join(prompt_parts)
    logging.debug(f"Sending diagram plan prompt to LLM (first 1000 chars):\n{full_prompt[:1000]}...")

    plan_data = None
    retries = 2 # Initial attempt + 2 retries = 3 total attempts
    for i in range(retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=full_prompt,
            )
            generated_json_str = response.text.strip()
            logging.debug(f"Raw diagram plan JSON from LLM (attempt {i+1}/{retries+1}): {generated_json_str}")

            # Clean markdown code block if present
            if generated_json_str.startswith("```json") and generated_json_str.endswith("```"):
                generated_json_str = generated_json_str[len("```json"):-len("```")].strip()
            
            plan_data = json.loads(generated_json_str)
            logging.debug(f"Parsed diagram plan: {plan_data}")
            break # Successfully parsed
        except json.JSONDecodeError as e:
            logging.warning(f"Failed to parse diagram plan JSON from LLM (attempt {i+1}/{retries+1}): {e}. Raw response: {generated_json_str}", exc_info=True)
            if i < retries:
                logging.info("Retrying diagram plan generation with stricter prompt...")
                # For retry, append a reminder about strict JSON
                full_prompt += "\n\nCRITICAL: The previous response was not valid JSON. You MUST return only a valid JSON object as specified, with no extra text or markdown wrappers."
                time.sleep(2) # Wait a bit before retrying
            else:
                logging.error(f"Failed to parse diagram plan JSON after {retries + 1} attempts. Giving up.")
                return None
        except Exception as e:
            logging.error(f"Gemini generation failed for diagram plan (attempt {i+1}/{retries+1}): {e}", exc_info=True)
            if i < retries:
                logging.info("Retrying diagram plan generation after general error...")
                time.sleep(2)
            else:
                logging.error(f"Failed to generate diagram plan after {retries+1} attempts due to general error.")
                return None

    if plan_data and validate_diagram_plan(plan_data):
        return plan_data
    else:
        logging.error("Generated diagram plan failed validation.")
        return None

def validate_diagram_plan(plan: Dict[str, Any]) -> bool:
    """
    Validates the structure and content of the AI-generated diagram plan.
    """
    if not isinstance(plan, dict):
        logging.error("Diagram plan is not a dictionary.")
        return False
    
    required_keys = ["project_topic", "architecture_style", "nodes", "edges", "summary_bullets"]
    if not all(key in plan for key in required_keys):
        logging.error(f"Diagram plan missing required keys. Found: {plan.keys()}, Expected: {required_keys}")
        return False

    # Validate nodes
    nodes = plan.get("nodes", [])
    if not (4 <= len(nodes) <= 8):
        logging.error(f"Invalid number of nodes: {len(nodes)}. Expected 4-8.")
        return False
    
    node_ids = set()
    allowed_layers = {"UI Layer", "API Layer", "Processing Layer", "AI Layer", "Data/Storage Layer"}
    for node in nodes:
        if not isinstance(node, dict) or "id" not in node or "label" not in node or "layer" not in node:
            logging.error(f"Malformed node entry (missing id, label, or layer): {node}")
            return False
        if not re.fullmatch(r"[A-Z]", node["id"]):
            logging.error(f"Invalid node ID format: {node['id']}. Expected single uppercase letter.")
            return False
        if not isinstance(node["label"], str) or not node["label"].strip():
            logging.error(f"Node label is empty or not a string: {node['label']}.")
            return False
        if node["id"] in node_ids:
            logging.error(f"Duplicate node ID: {node['id']}")
            return False
        if node["layer"] not in allowed_layers:
            logging.error(f"Invalid node layer: {node['layer']}. Expected one of {allowed_layers}.")
            return False
        node_ids.add(node["id"])

    # Validate edges
    edges = plan.get("edges", [])
    for edge in edges:
        # Edge labels are no longer expected
        if not isinstance(edge, dict) or "from" not in edge or "to" not in edge:
            logging.error(f"Malformed edge entry (missing from or to): {edge}")
            return False
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            logging.error(f"Edge references non-existent node ID: {edge}")
            return False

    # Validate summary bullets
    summary_bullets = plan.get("summary_bullets", [])
    if not (2 <= len(summary_bullets) <= 4):
        logging.error(f"Invalid number of summary bullets: {len(summary_bullets)}. Expected 2-4.")
        return False
    for bullet in summary_bullets:
        if not isinstance(bullet, str) or not bullet.strip():
            logging.error(f"Summary bullet is empty or not a string: {bullet}.")
            return False
            
    return True

def diagram_plan_to_mermaid(plan: Dict[str, Any]) -> str:
    """
    Converts a validated diagram plan into a Mermaid flowchart LR string with subgraphs.
    Quotes all node labels. Edges do not have labels.
    """
    diagram_lines = ["%%{init: {'flowchart': {'nodeSpacing': 50, 'rankSpacing': 70}}}%%", "flowchart LR"]
    
    nodes = plan.get("nodes", [])
    edges = plan.get("edges", [])

    # Group nodes by layer
    layers = {
        "UI Layer": [],
        "API Layer": [],
        "Processing Layer": [],
        "AI Layer": [],
        "Data/Storage Layer": []
    }
    for node in nodes:
        if node["layer"] in layers:
            layers[node["layer"]].append(node)
        else:
            # Fallback for unexpected layers, though validation should prevent this
            logging.warning(f"Node {node['id']} has unrecognized layer '{node['layer']}'. Assigning to 'Generic Layer'.")
            if "Generic Layer" not in layers:
                layers["Generic Layer"] = []
            layers["Generic Layer"].append(node)


    # Define subgraphs and nodes within them
    for layer_name, layer_nodes in layers.items():
        if layer_nodes:
            # Use a simpler subgraph name for Mermaid syntax
            mermaid_subgraph_name = layer_name.replace(" ", "_").replace("/", "_").replace("-", "_")
            diagram_lines.append(f"  subgraph {mermaid_subgraph_name} [\"{layer_name}\"]")
            for node in layer_nodes:
                # Node labels can contain \n, so don't replace them, only quotes
                sanitized_label = node["label"].replace('"', "'").strip()
                diagram_lines.append(f"    {node['id']}[\"{sanitized_label}\"]")
            diagram_lines.append("  end")

    # Define connections without edge labels
    for edge in edges:
        diagram_lines.append(f"  {edge['from']} --> {edge['to']}")
    
    return "\n".join(diagram_lines)

def insert_ai_diagram_into_architecture_section(base_readme_content: str, diagram_plan: Dict[str, Any], mermaid_diagram: str) -> str:
    """
    Inserts the AI-generated diagram and summary into the Architecture section of the README.
    """
    architecture_section_markdown = "\n## Architecture\n\n"
    
    project_topic = diagram_plan.get("project_topic", "The project's architecture")
    architecture_section_markdown += f"{project_topic}.\n\n"

    architecture_section_markdown += "```mermaid\n"
    architecture_section_markdown += mermaid_diagram
    architecture_section_markdown += "\n```\n"
    architecture_section_markdown += f"\nFor a standalone preview, see [docs/architecture.html](docs/architecture.html).\n"

    architecture_section_markdown += "\n### Key Architectural Aspects:\n"
    for bullet in diagram_plan.get("summary_bullets", []):
        architecture_section_markdown += f"* {bullet}\n"
    
    # We defined the prompt *not* to include "## Architecture", so we just append it.
    return base_readme_content + architecture_section_markdown

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
        
        # New error handling specifically for the 409 conflict: file blocking directory creation
        if e.response.status_code == 409 and "file exists where you’re trying to create a subdirectory" in error_details:
            logging.warning(f"Conflict detected: A file is blocking directory creation for '{file_path_str}'. Attempting to resolve...")
            
            # The conflicting path is the parent directory (e.g., 'docs' for 'docs/architecture.mmd').
            parent_dir_path_in_repo = file_path_in_repo.parent
            
            # Ensure it's not trying to delete the root of the repo (empty path or '.' for current dir)
            if parent_dir_path_in_repo and str(parent_dir_path_in_repo) != '.':
                conflicting_path_str = str(parent_dir_path_in_repo)
                conflicting_url = f"https://api.github.com/repos/{full_github_repo}/contents/{conflicting_path_str}"

                # 1. Get SHA of the conflicting file (e.g., 'docs')
                try:
                    get_response = requests.get(conflicting_url, headers=headers)
                    if get_response.status_code == 200:
                        conflicting_file_data = get_response.json()
                        # Ensure it's a file, not a directory before attempting to delete
                        if conflicting_file_data.get('type') == 'file':
                            conflicting_sha = conflicting_file_data['sha']
                            logging.info(f"Found conflicting file at '{conflicting_path_str}' with SHA: {conflicting_sha}. Attempting to delete it.")

                            # 2. Attempt to delete the conflicting file
                            delete_payload = {
                                "message": f"chore: delete conflicting file '{conflicting_path_str}' to enable directory creation",
                                "sha": conflicting_sha,
                                "branch": branch
                            }
                            delete_response = requests.delete(conflicting_url, headers=headers, json=delete_payload)
                            delete_response.raise_for_status()
                            logging.info(f"Successfully deleted conflicting file '{conflicting_path_str}'. Retrying original publish.")

                            # 3. Retry the original PUT operation
                            retry_response = requests.put(url, headers=headers, json=payload)
                            retry_response.raise_for_status()
                            logging.info(f"Successfully {action_performed} '{file_path_str}' for '{full_github_repo}' on branch '{branch}' after conflict resolution.")
                            return {"status": "SUCCESS", "action": action_performed, "file_path": file_path_str, "retried": True}
                        else:
                            logging.warning(f"Conflicting path '{conflicting_path_str}' is not a file (it's a {conflicting_file_data.get('type')}). Cannot resolve conflict automatically by deletion.")
                    elif get_response.status_code == 404:
                        logging.warning(f"Conflicting file at '{conflicting_path_str}' not found during re-check, despite 409. This is unexpected. Not attempting delete.")
                    else:
                        logging.warning(f"Could not retrieve conflicting file info for '{conflicting_path_str}': {get_response.status_code} - {get_response.text}. Cannot resolve conflict automatically.")
                except requests.exceptions.RequestException as retry_e:
                    logging.error(f"Error during conflict resolution (GET/DELETE) for '{file_path_str}': {retry_e}", exc_info=True)
                except Exception as retry_e:
                    logging.error(f"Unexpected error during conflict resolution (GET/DELETE) for '{file_path_str}': {retry_e}", exc_info=True)
            else:
                logging.warning(f"Conflicting path for '{file_path_str}' is at repository root or empty. Automatic deletion of root-level conflicting files is not supported to prevent accidental repo damage.")
        
        return {"status": "FAILED", "file_path": file_path_str, "reason": f"HTTPError {e.response.status_code}: {error_details}"}
    except requests.exceptions.RequestException as e:
        # Check for specific "Branch not found" error when it's an API PUT failure
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404 and "Branch main not found" in e.response.json().get('message', ''):
            logging.warning(f"Branch '{branch}' not found for '{full_github_repo}'. Attempting to detect default branch...")
            repo_api_url = f"https://api.github.com/repos/{full_github_repo}"
            try:
                repo_info_response = requests.get(repo_api_url, headers=headers)
                repo_info_response.raise_for_status()
                repo_info = repo_info_response.json()
                default_branch = repo_info.get('default_branch')

                if default_branch and default_branch != branch:
                    logging.info(f"Detected default branch as '{default_branch}'. Retrying publish to '{default_branch}'.")
                    # Update payload and retry with the correct default branch
                    payload["branch"] = default_branch
                    commit_message_action = "add" if file_path_str == "README.md" else "create"
                    commit_message_type = "docs" if file_path_str.startswith("docs/") or file_path_str == "README.md" else "feat"
                    payload["message"] = f"{commit_message_type}: {commit_message_action} {file_path_str}"
                    
                    retry_response = requests.put(url, headers=headers, json=payload)
                    retry_response.raise_for_status()
                    logging.info(f"Successfully {action_performed} '{file_path_str}' for '{full_github_repo}' on branch '{default_branch}' after branch detection.")
                    return {"status": "SUCCESS", "action": action_performed, "file_path": file_path_str, "retried_branch": True}
                else:
                    logging.warning(f"Could not determine a different default branch or default branch is still '{branch}'.")

            except requests.exceptions.RequestException as retry_e:
                logging.error(f"Error during default branch detection or retry for '{full_github_repo}': {retry_e}", exc_info=True)
            except Exception as retry_e:
                logging.error(f"Unexpected error during default branch detection or retry for '{full_github_repo}': {retry_e}", exc_info=True)

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
    parser.add_argument("--diagram-mode", type=str, choices=["ai", "none"], default="ai", 
                        help="Mode for generating architecture diagrams (default: ai). 'none' skips diagram generation.")
    args = parser.parse_args()

    if not args.repo and not args.all:
        parser.error("Please specify either --repo <full_name> or --all.")

    if args.diagram_mode == "none":
        logging.info("Diagram generation is disabled by --diagram-mode none.")

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

            # --- Generate Architecture Diagram components based on diagram_mode ---
            diagram_plan = None
            if args.diagram_mode == "ai":
                logging.info(f"Generating AI-driven diagram plan for '{full_name}'...")
                diagram_plan = generate_diagram_plan(repo_metadata, github_repo_context)

            if diagram_plan:
                mermaid_content = diagram_plan_to_mermaid(diagram_plan)
                if mermaid_content:
                    html_content = generate_architecture_html(mermaid_content, repo_name)
                    readme_content = insert_ai_diagram_into_architecture_section(readme_content, diagram_plan, mermaid_content)
                    logging.info(f"Generated AI-driven architecture diagram for '{full_name}'.")
                else:
                    logging.warning(f"Mermaid content generation failed from AI diagram plan for '{full_name}'. Falling back to bullet list.")
                    # Fallback to simple bullet list from plan summary if Mermaid generation fails
                    architecture_section_markdown = "\n## Architecture\n\n"
                    architecture_section_markdown += diagram_plan.get("project_topic", "The project's architecture") + ".\n\n"
                    architecture_section_markdown += "\n### Key Architectural Aspects:\n"
                    for bullet in diagram_plan.get("summary_bullets", []):
                        architecture_section_markdown += f"* {bullet}\n"
                    readme_content += architecture_section_markdown
            else:
                logging.warning(f"Skipping AI diagram generation or plan validation failed for '{full_name}'. Adding a simple placeholder.")
                architecture_section_markdown = "\n## Architecture\n\n* Architecture diagram could not be generated automatically. Please review the project manually.\n"
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
