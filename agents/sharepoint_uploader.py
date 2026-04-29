import os
import logging
import base64
import requests
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def upload_to_sharepoint(mp4_path: str, demo_title: str, description: str = "", timeout_s: int = 300) -> Dict[str, Any]:
    """
    Uploads an MP4 file to SharePoint via a Power Automate webhook.

    Args:
        mp4_path (str): The local path to the MP4 file to upload.
        demo_title (str): The title of the demo video.
        description (str): A description for the video, used in SharePoint.
        timeout_s (int): The timeout for the HTTP request in seconds.

    Returns:
        Dict[str, Any]: A dictionary containing the upload status and any
                        relevant information from the SharePoint webhook response.
                        Expected keys: 'status_code', 'filename', 'sharepoint_link' (optional).

    Raises:
        ValueError: If the SHAREPOINT_WEBHOOK_URL environment variable is not set.
        FileNotFoundError: If the mp4_path does not exist.
        requests.exceptions.RequestException: For any HTTP request-related errors,
                                              including non-200 status codes.
    """
    sharepoint_webhook_url = os.environ.get("SHAREPOINT_WEBHOOK_URL")
    if not sharepoint_webhook_url:
        raise ValueError("SHAREPOINT_WEBHOOK_URL environment variable not set. Skipping SharePoint upload.")

    file_path = Path(mp4_path)
    if not file_path.exists():
        raise FileNotFoundError(f"MP4 file not found at: {mp4_path}")

    filename = file_path.name
    
    logger.info(f"Preparing to upload {filename} to SharePoint...")

    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')

        payload = {
            "filename": filename,
            "file_b64": file_b64,
            "demo_title": demo_title,
            "description": description,
        }

        response = requests.post(sharepoint_webhook_url, json=payload, timeout=timeout_s)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        response_json = {}
        try:
            # Attempt to parse JSON, but handle cases where body might be empty
            if response.text:
                response_json = response.json()
        except requests.exceptions.JSONDecodeError:
            logger.warning(f"SharePoint webhook returned non-JSON response: {response.text[:200]}")
            response_json = {"message": response.text} # Store raw text if not JSON

        result = {
            "status_code": response.status_code,
            "filename": filename,
            **response_json # Merge any parsed JSON into result
        }

        logger.info(f"Successfully uploaded {filename} to SharePoint. Status: {response.status_code}")
        if 'sharepoint_link' in response_json:
            logger.info(f"SharePoint link: {response_json['sharepoint_link']}")
        
        return result

    except requests.exceptions.HTTPError as http_err:
        error_detail = f"SharePoint upload failed with HTTP error {http_err.response.status_code}: {http_err.response.text}"
        logger.error(error_detail)
        raise requests.exceptions.RequestException(error_detail) from http_err
    except requests.exceptions.ConnectionError as conn_err:
        error_detail = f"SharePoint upload failed due to connection error: {conn_err}"
        logger.error(error_detail)
        raise requests.exceptions.RequestException(error_detail) from conn_err
    except requests.exceptions.Timeout as timeout_err:
        error_detail = f"SharePoint upload timed out after {timeout_s} seconds: {timeout_err}"
        logger.error(error_detail)
        raise requests.exceptions.RequestException(error_detail) from timeout_err
    except requests.exceptions.RequestException as req_err:
        error_detail = f"An unknown request error occurred during SharePoint upload: {req_err}"
        logger.error(error_detail)
        raise # Re-raise the caught exception
    except Exception as e:
        error_detail = f"An unexpected error occurred during SharePoint upload: {type(e).__name__} - {e}"
        logger.error(error_detail)
        raise # Re-raise any other unexpected exceptions


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m agents.sharepoint_uploader <mp4_path> <title> [description]")
        sys.exit(1)

    mp4_file = sys.argv[1]
    video_title = sys.argv[2]
    video_description = sys.argv[3] if len(sys.argv) > 3 else ""

    # Set a dummy webhook URL for testing if not set in env
    if not os.environ.get("SHAREPOINT_WEBHOOK_URL"):
        print("WARNING: SHAREPOINT_WEBHOOK_URL not set. Using a dummy URL for testing.")
        os.environ["SHAREPOINT_WEBHOOK_URL"] = "http://localhost:9999/dummy-webhook" # Use a non-existent URL

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    try:
        print(f"Attempting to upload '{mp4_file}' with title '{video_title}' and description '{video_description}'...")
        upload_result = upload_to_sharepoint(mp4_file, video_title, video_description)
        print("\nSharePoint Upload Result:")
        for k, v in upload_result.items():
            print(f"- {k}: {v}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error during SharePoint upload: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
````

Next, I will modify `api/main.py` to import the new agent and integrate the upload step into the video job functions.

````python
api/main.py
<<<<<<< SEARCH
# Import agents
# These imports are critical; if they fail, the app shouldn't start.
from agents.transcript_agent import generate_transcript
from agents.github_reader_agent import get_repo_context # New import
from agents.tts_agent import text_to_mp3
from agents.gcs_agent import upload_to_gcs
from agents.video_agent import mp3_to_video
from google import genai
from google.genai import types as genai_types
