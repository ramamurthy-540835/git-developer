import os
from google import genai
import logging # Import logging for consistency

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            raise ValueError("Missing GOOGLE_CLOUD_PROJECT or GCP_PROJECT_ID for Vertex AI.")
            
        return genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )
    except Exception as e:
        logging.error(f"Failed to initialize genai client with Vertex AI: {e}. Please ensure gcloud is configured or an API key is provided.")
        raise # Re-raise to indicate client creation failure

client = create_genai_client()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash") # Define model name

def generate_script(prompt: str) -> str:
    """
    Generates a short narration script (2-3 minutes) using the Gemini 2.5 Flash model.

    Args:
        prompt (str): The topic or idea for the script.

    Returns:
        str: A plain text narration script.
    """
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt
    )
    # Ensure to return only the text content, strip any leading/trailing whitespace/newlines
    return response.text.strip()
