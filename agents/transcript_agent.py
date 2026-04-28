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
    prompt_parts = [
        f"Generate a voiceover-ready transcript for an enterprise demo of the application '{app_name}'.",
        f"The transcript should be 60-90 seconds long and maintain an enterprise demo tone.",
        f"Application details: Name: '{app_name}', Description: '{app_description}', URL: '{app_url}'.",
        "Explain actual visible features from the page. Mention dashboards, agents, filters, cards, metrics, and workflows only if they are explicitly present or implied in the provided content. Avoid hallucinating features not visible in the URL content.",
        "Output the transcript directly, without any markdown, bullet points, or introductory/concluding remarks."
    ]

    if url_read_successful:
        prompt_parts.append("\n--- Visible Page Content (extracted from URL) ---\n")
        if source_context["title"] and source_context["title"] != "Error reading page":
            prompt_parts.append(f"Page Title: {source_context['title']}\n")
        if source_context["headings"]:
            prompt_parts.append(f"Headings found: {', '.join(source_context['headings'])}\n")
        if source_context["buttons"]:
            prompt_parts.append(f"Button labels found: {', '.join(source_context['buttons'])}\n")
        if source_context["cards"]:
            prompt_parts.append(f"Card titles/key sections found: {', '.join(source_context['cards'])}\n")
        if source_context["tables"]:
            table_summaries = []
            for table in source_context["tables"]:
                table_caption = f" (Caption: {table['caption']})" if table['caption'] else ""
                table_summaries.append(f"Table with headers: {', '.join(table['headers'])}{table_caption}")
            prompt_parts.append(f"Table structures found: {'; '.join(table_summaries)}\n")
        # Include raw text for broader context for the LLM
        if page_content.get("raw_text"):
            prompt_parts.append(f"Raw visible text snippet: {page_content['raw_text']}\n")
    elif app_url and "Error" in page_content.get("title", ""):
        prompt_parts.append(f"\n--- URL Reading Error ---\n")
        prompt_parts.append(f"Attempted to read URL: {app_url}\n")
        prompt_parts.append(f"Error encountered: {page_content.get('raw_text', 'No specific error message available.')}\n")
        prompt_parts.append(f"Please generate the transcript based on the application metadata provided, acknowledging that page content could not be fully accessed.")


    final_prompt = "\n".join(prompt_parts)
    logging.info(f"Sending prompt to LLM (first 500 chars):\n---\n{final_prompt[:500]}...\n---\n")

    # Call the LLM to generate the transcript
    try:
        transcript = call_llm_generate_script(final_prompt)
    except Exception as e:
        logging.error(f"LLM failed to generate transcript: {e}", exc_info=True)
        transcript = f"Failed to generate transcript due to an internal LLM error. Please try again. Details: {str(e)}"

    if warning_message:
        # Prepend warning to transcript if there was an issue reading URL content
        transcript = f"[WARNING: {warning_message}]\n\n{transcript}"

    return transcript, source_context
