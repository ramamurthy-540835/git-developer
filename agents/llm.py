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

    full_prompt = (
        f"Generate a narration script for a video. "
        f"The script should be approximately 2-3 minutes long when narrated. "
        f"It should be plain text, without any formatting like bolding or headings. "
        f"The topic of the script is: {prompt}"
    )

    response = model.generate_content(full_prompt)
    return response.text
