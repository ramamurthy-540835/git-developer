import os
import logging
import asyncio
from agents.url_reader_agent import read_app_url
from agents.llm import generate_script as call_llm_generate_script # Direct import now that agents/llm.py is available

logging.basicConfig(level=logging.INFO)

async def generate_transcript(app: dict) -> tuple[str, dict]:
    """
    Generates a voiceover-ready transcript for an application, incorporating
    content read directly from the application's URL.
    Returns the transcript string and a dictionary of source page context.
    """
    app_url = app.get("url")
    app_name = app.get("name", "Unknown Application").replace('_', ' ').title()
    app_description = app.get("description", "No description provided.")

    source_context = {
        "title": "N/A",
        "url": app_url,
        "headings": [],
        "buttons": [],
        "cards": [],
        "tables": [],
    }
    url_read_successful = False
    warning_message = ""
    page_content = {}

    if app_url:
        logging.info(f"Reading URL content for {app_name} from {app_url}")
        page_content = await read_app_url(app_url)
        
        # Populate source_context with actual data, even if error occurred, to show error details
        source_context = {
            "title": page_content.get("title", "Error reading page"),
            "url": page_content.get("url", app_url),
            "headings": page_content.get("headings", []),
            "buttons": page_content.get("buttons", []),
            "cards": page_content.get("cards", []),
            "tables": page_content.get("tables", []),
        }
        
        # Check if URL reading was genuinely successful (no "Error" in title and some content)
        if "Error" not in page_content.get("title", "") and any([
            page_content.get("headings"),
            page_content.get("buttons"),
            page_content.get("cards"),
            page_content.get("tables"),
            page_content.get("raw_text")
        ]):
            url_read_successful = True
            logging.info(f"Successfully read URL content for {app_name}.")
        else:
            warning_message = "URL content could not be fully read or contained no relevant visible features. Transcript generated primarily from metadata."
            logging.warning(f"For {app_name}: {warning_message}")
    else:
        warning_message = "Application URL not provided. Transcript generated from metadata only."
        logging.warning(warning_message)

    # Construct the prompt for Gemini
    prompt_parts = []

    base_instruction = "Generate only a voiceover narration script for an enterprise demo. " \
                       "The script should be 60-90 seconds long and maintain a professional, confident, and informative enterprise demo tone. " \
                       "Do not include any introductory phrases like 'Here is the transcript' or 'Welcome to the demo'. " \
                       "Do not use markdown formatting (like bolding, italics, or headings) or bullet points. " \
                       "Focus solely on explaining the application's features and benefits as if you are narrating a live demonstration. " \
                       "Avoid any commentary about writing the script itself, technical access issues, or placeholder text."

    prompt_parts.append(base_instruction)

    # Use enriched metadata for prompting
    app_title = app.get("title", app_name) # Use 'title' from config if present
    app_tags = app.get("tags", [])

    prompt_parts.append(f"\n\nApplication being demonstrated: {app_title}")
    prompt_parts.append(f"Primary purpose: {app_description}")
    if app_url:
        prompt_parts.append(f"Application URL: {app_url}")
    if app_tags:
        prompt_parts.append(f"Key themes/tags: {', '.join(app_tags)}")

    # Specific guidance for VBC Dashboard
    if app_name.lower().replace(' ', '_') == 'vbc_dashboard':
        prompt_parts.append("\n\nFocus for VBC Dashboard narration:")
        prompt_parts.append("- Start by addressing the core business problem in healthcare value-based care.")
        prompt_parts.append("- Clearly explain the dashboard's purpose in solving this problem.")
        prompt_parts.append("- Detail key features like risk stratification, identifying high-risk patients, highlighting care gaps, tracking quality measures, and supporting care management workflows. If specific buttons or headings for these are found in the URL content, mention them naturally.")
        prompt_parts.append("- Emphasize how the platform leverages AI for insights (as described in the metadata or observed).")
        prompt_parts.append("- Explain the value proposition for care managers, providers, executives, and payer teams.")
        prompt_parts.append("- Conclude with a strong statement about the business outcomes achieved.")
        prompt_parts.append("- Prioritize using the provided detailed description and tags for domain knowledge. Do not hallucinate exact numbers unless present in the visible page content.")

    # General guidance if URL content is available
    if url_read_successful:
        prompt_parts.append("\n\nVisible elements from the live application page (integrate these naturally into the narration if relevant to features):")
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
        if page_content.get("raw_text"):
            prompt_parts.append(f"Snippet of raw visible page text (for additional context): {page_content['raw_text']}")
    elif app_url and "Error" in page_content.get("title", ""):
        prompt_parts.append(f"\n\nNote: The application URL '{app_url}' could not be fully accessed or provided meaningful visible content. Please generate the narration based primarily on the application's title, description, and domain knowledge (including tags), maintaining an informative tone without mentioning this technical access issue within the narration itself.")

    final_prompt = "\n".join(prompt_parts)
    logging.info(f"Sending prompt to LLM (first 500 chars):\n---\n{final_prompt[:500]}...\n---\n")

    # Call the LLM to generate the transcript
    try:
        transcript = call_llm_generate_script(final_prompt)
    except Exception as e:
        logging.error(f"LLM failed to generate transcript: {e}", exc_info=True)
        transcript = f"An internal system error occurred while generating the transcript. Please try again."
        # The warning message will be set below if it's due to URL read failure
        if not warning_message: # If LLM failed, but URL was readable, then this is an LLM specific error.
             warning_message = f"LLM generation failed: {str(e)}"


    # Return the transcript, source context, and the warning message separately
    return transcript, source_context, warning_message
