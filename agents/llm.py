import os
import google.generativeai as genai

# Configure the API key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_script(prompt: str) -> str:
    """
    Generates a short narration script (2-3 minutes) using the Gemini 2.5 Flash model.

    Args:
        prompt (str): The topic or idea for the script.

    Returns:
        str: A plain text narration script.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')

    response = model.generate_content(prompt)
    # Ensure to return only the text content, strip any leading/trailing whitespace/newlines
    return response.text.strip()
