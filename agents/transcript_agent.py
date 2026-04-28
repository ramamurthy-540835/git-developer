import os
import logging
import asyncio
from typing import Dict, Any # Import Dict and Any
from agents.url_reader_agent import read_app_url
from agents.github_reader_agent import get_repo_context # New import
from agents.llm import generate_script as call_llm_generate_script

logging.basicConfig(level=logging.INFO)

async def generate_transcript(app: dict) -> tuple[str, dict, str]:
    """
    Generates a voiceover-ready transcript for an application, incorporating
    content read either from its GitHub repository or live URL.
    Returns the transcript string, a dictionary of source context, and a warning message.
    """
    app_url = app.get("url")
    repo_url = app.get("repo_url") # New: get repo_url
    app_name = app.get("name", "Unknown Application").replace('_', ' ').title()
    app_description = app.get("description", "No description provided.")
    app_title = app.get("title", app_name) # Use 'title' from config if present
    app_tags = app.get("tags", [])

import os
import logging
import asyncio
from typing import Dict, Any, List # Import List as well
from agents.url_reader_agent import read_app_url
from agents.github_reader_agent import get_repo_context
from agents.llm import generate_script as call_llm_generate_script

logging.basicConfig(level=logging.INFO)

async def generate_transcript(app: Dict[str, Any]) -> tuple[str, Dict[str, Any], str]:
    """
    Generates a voiceover-ready transcript for an application, incorporating
    content read either from its GitHub repository or live URL.
    Returns the transcript string, a dictionary of source context, and a warning message.
    """
    # Use repo_url if available, otherwise fallback to url
    repo_url = app.get("repo_url")
    app_url = app.get("url") 
    
    app_name = app.get("name", "Unknown Application").replace('_', ' ').title()
    app_full_name = app.get("full_name", app_name) # New: for GitHub full name
    app_description = app.get("description", "No description provided.")
    app_title = app.get("title", app_name) # Use 'title' from config if present, fallback to name
    app_tags = app.get("tags", [])
    
    source_context: Dict[str, Any] = {
        "type": "N/A", 
        "title": app_title,
        "url": app_url,
        "repo_url": repo_url,
        "headings": [], "buttons": [], "cards": [], "tables": [], # Web page specific
        "repo_name": app_name, # GitHub specific
        "repo_full_name": app_full_name, # GitHub specific
        "repo_description": app_description, # GitHub specific
        "readme_preview": "N/A", # GitHub specific
        "tech_stack": [], # GitHub specific
        "detected_features": [], # GitHub specific
    }
    content_read_successful = False
    warning_message = ""
    extracted_content: Dict[str, Any] = {} # This will hold either page_content or repo_context

    if repo_url:
        logging.info(f"Attempting to read GitHub repo context for {app_full_name} from {repo_url}")
        extracted_content = get_repo_context(repo_url) # Synchronous call to GitHub API
        source_context["type"] = "github_repo"
        source_context["repo_name"] = extracted_content.get("name", app_name)
        source_context["repo_full_name"] = app_full_name
        source_context["repo_description"] = extracted_content.get("description", app_description)
        source_context["readme_preview"] = extracted_content.get("readme", "No README content available.")
        source_context["tech_stack"] = extracted_content.get("tech_stack", [])
        source_context["detected_features"] = extracted_content.get("features", [])
        source_context["url"] = repo_url # Set primary URL in context to repo_url

        if "Error" not in extracted_content.get("name", ""):
            content_read_successful = True
            logging.info(f"Successfully read GitHub repo context for {app_full_name}.")
        else:
            warning_message = f"GitHub repository content could not be fully read from {repo_url}. {extracted_content.get('description', '')} Transcript generated primarily from app metadata."
            logging.warning(f"For {app_full_name}: {warning_message}")
    elif app_url:
        logging.info(f"Reading URL content for {app_name} from {app_url}")
        page_content = await read_app_url(app_url)
        extracted_content = page_content
        source_context["type"] = "web_page"
        source_context["title"] = page_content.get("title", "Error reading page")
        source_context["url"] = page_content.get("url", app_url)
        source_context["headings"] = page_content.get("headings", [])
        source_context["buttons"] = page_content.get("buttons", [])
        source_context["cards"] = page_content.get("cards", [])
        source_context["tables"] = page_content.get("tables", [])

        if "Error" not in page_content.get("title", "") and any([
            page_content.get("headings"),
            page_content.get("buttons"),
            page_content.get("cards"),
            page_content.get("tables"),
            page_content.get("raw_text")
        ]):
            content_read_successful = True
            logging.info(f"Successfully read URL content for {app_name}.")
        else:
            warning_message = "URL content could not be fully read or contained no relevant visible features. Transcript generated primarily from metadata."
            logging.warning(f"For {app_name}: {warning_message}")
    else:
        warning_message = "Application URL or Repository URL not provided. Transcript generated from metadata only."
        logging.warning(warning_message)

    # Construct the prompt for Gemini
    prompt_parts: List[str] = []
    base_instruction = "Your task is to generate ONLY a compelling, voiceover-ready narration script for an enterprise application demo. " \
                       "The script MUST be between 60 to 90 seconds long when spoken and must maintain a professional, confident, and highly informative enterprise demo tone. " \
                       "STRICTLY adhere to these formatting rules: Do NOT include any introductory or concluding meta-commentary (e.g., 'Here is the transcript', 'Welcome to the demo'). " \
                       "Do NOT use any markdown formatting (e.g., bolding, italics, headings) or bullet points. " \
                       "Focus entirely on explaining the application's features, benefits, and value proposition as if you are narrating a live demonstration. " \
                       "Crucially, DO NOT mention any technical issues, URL access problems, or script-writing instructions within the narration itself. " \
                       "Output ONLY the final voiceover narration."
    prompt_parts.append(base_instruction)

    prompt_parts.append(f"\n\nApplication being demonstrated: {app_title}")
    prompt_parts.append(f"Primary purpose: {app_description}")
    if app_tags:
        prompt_parts.append(f"Key themes/tags: {', '.join(app_tags)}")

    if content_read_successful:
        if source_context["type"] == "github_repo":
            prompt_parts.append(f"\n\nContext extracted from GitHub repository ({repo_url}):")
            prompt_parts.append(f"Repository Full Name: {source_context['repo_full_name']}")
            prompt_parts.append(f"Repository Description: {source_context['repo_description']}")
            if source_context["tech_stack"]:
                prompt_parts.append(f"Detected Technologies/Stack: {', '.join(source_context['tech_stack'])}")
            if source_context["detected_features"]:
                prompt_parts.append(f"Inferred Features/Capabilities: {', '.join(source_context['detected_features'])}")
            if source_context["readme_preview"] and source_context["readme_preview"] != "No README.md found.":
                prompt_parts.append(f"README.md Content Preview (for additional detail on functionality): {source_context['readme_preview']}")
            # Instruct LLM to infer UI flows from code structure and readme
            prompt_parts.append("Based on the repository context (README, files, tech stack, inferred features), describe the expected user interface (UI) flows, key functionalities, and user interactions of the application as if you are walking through them visually. Emphasize the 'how it works' from a user perspective.")
        elif source_context["type"] == "web_page":
            prompt_parts.append(f"\n\nVisible elements from the live application page ({app_url}, integrate these naturally into the narration if relevant to features):")
            if source_context["title"] and source_context["title"] != "Error reading page":
                prompt_parts.append(f"Page Title: {source_context['title']}")
            if source_context["headings"]:
                prompt_parts.append(f"Visible Headings: {', '.join(source_context['headings'])}")
            if source_context["buttons"]:
                prompt_parts.append(f"Visible Buttons: {', '.join(source_context['buttons'])}")
            if source_context["cards"]:
                prompt_parts.append(f"Visible Card Titles/Sections: {', '.join(source_context['cards'])}")
            if source_context["tables"]:
                table_summaries = []
                for table in source_context["tables"]:
                    table_caption = f" (Caption: {table['caption']})" if table['caption'] else ""
                    table_summaries.append(f"Table with headers: {', '.join(table['headers'])}{table_caption}")
                prompt_parts.append(f"Visible Table Structures: {'; '.join(table_summaries)}")
            if extracted_content.get("raw_text"):
                prompt_parts.append(f"Snippet of raw visible page text (for additional context, filter strictly for relevance to features): {extracted_content['raw_text']}")
    else:
        # Fallback if no content could be read from either source
        if repo_url and "Error" in extracted_content.get("name", ""):
            prompt_parts.append(f"\n\nIMPORTANT: The GitHub repository at '{repo_url}' could not be fully accessed or yielded insufficient content. Generate narration based SOLELY on the provided application title, description, and key themes/tags. Do NOT mention the access issue in the final narration.")
        elif app_url and "Error" in extracted_content.get("title", ""):
            prompt_parts.append(f"\n\nIMPORTANT: The live application at '{app_url}' could not be fully accessed or yielded insufficient visible content. Generate narration based SOLELY on the provided application title, description, and key themes/tags. Do NOT mention the access issue in the final narration.")
        else: # Generic case if neither URL nor Repo URL provided, or generic failure
             prompt_parts.append("\n\nIMPORTANT: No external content (GitHub or URL) could be retrieved for this application. Generate the narration based SOLELY on the provided application title, description, and key themes/tags (domain knowledge).")

    # Specific guidance for VBC Dashboard (after general content context)
    # The 'name' field in app config is 'healthcare-vbc-pa', so match against that.
    if app.get("name", "").lower().replace(' ', '_') == 'healthcare-vbc-pa':
        prompt_parts.append("\n\nFurther Focus for Value-Based Care Dashboard narration (integrate if consistent with above context):")
        prompt_parts.append("- Start by addressing the core business problem in healthcare value-based care.")
        prompt_parts.append("- Clearly explain the dashboard's purpose in solving this problem.")
        prompt_parts.append("- Detail key features like risk stratification, identifying high-risk patients, highlighting care gaps, tracking quality measures, and supporting care management workflows. If specific buttons or headings for these are found in the URL/repo content, mention them naturally.")
        prompt_parts.append("- Emphasize how the platform leverages AI for insights (as described in the metadata or observed).")
        prompt_parts.append("- Explain the value proposition for care managers, providers, executives, and payer teams.")
        prompt_parts.append("- Conclude with a strong statement about the business outcomes achieved.")
        prompt_parts.append("- Prioritize using the provided detailed description and tags for domain knowledge. Do not hallucinate exact numbers unless present in the visible page/repo content.")


    final_prompt = "\n".join(prompt_parts)
    logging.info(f"Sending prompt to LLM (first 500 chars):\n---\n{final_prompt[:500]}...\n---\n")

    # Call the LLM to generate the transcript
    try:
        transcript = call_llm_generate_script(final_prompt)
    except Exception as e:
        logging.error(f"LLM failed to generate transcript: {e}", exc_info=True)
        transcript = f"An internal system error occurred while generating the transcript. Please try again."
        if not warning_message: # If LLM failed, but content was readable, then this is an LLM specific error.
             warning_message = f"LLM generation failed: {str(e)}"

    return transcript, source_context, warning_message
