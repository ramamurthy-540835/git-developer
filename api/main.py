import os
import asyncio
import logging
import yaml
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env.local if present
load_dotenv(dotenv_path='./.env.local')

# Import agents
# These imports are critical; if they fail, the app shouldn't start.
from agents.transcript_agent import generate_transcript
from agents.github_reader_agent import get_repo_context # New import
from agents.tts_agent import text_to_mp3
from agents.gcs_agent import upload_to_gcs


# Initialize FastAPI app
app = FastAPI(title="GCP Studio Media Agent")

# Pydantic model for repo context request
class RepoContextRequest(BaseModel):
    repo_url: str

# Add CORS middleware
origins = [
    "http://localhost:3000",
    "http://10.100.15.44:3000", # As per user request
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class AppData(BaseModel):
    name: str
    full_name: str # The owner/repo string
    repo_url: str
    url: Optional[str] = None # Keeping for backward compatibility if needed, but not primary
    description: Optional[str] = None
    language: Optional[str] = None
    private: Optional[bool] = None
    updated_at: Optional[str] = None
    tags: Optional[List[str]] = None

class TranscriptRequest(BaseModel):
    app: AppData # This will contain the full repo details from repos.yaml

class Mp3GenerateRequest(BaseModel):
    name: str
    transcript: str

# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/repos")
async def get_all_repos():
    """
    Reads config/repos.yaml and returns the list of all configured repositories.
    """
    try:
        with open("config/repos.yaml", "r") as f:
            repos_config = yaml.safe_load(f)
        return {"repos": repos_config.get("repos", [])}
    except FileNotFoundError:
        logging.error("config/repos.yaml not found", exc_info=True)
        raise HTTPException(status_code=404, detail="Repository configuration file not found.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config/repos.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing repository configuration: {e}")

@app.get("/api/repos/{owner_repo:path}")
async def get_repo_by_full_name(owner_repo: str):
    """
    Reads config/repos.yaml and returns details for a specific repository by its full name (owner/repo).
    """
    try:
        with open("config/repos.yaml", "r") as f:
            repos_config = yaml.safe_load(f)
        repos = repos_config.get("repos", [])
        
        for repo_data in repos:
            if repo_data.get("full_name") == owner_repo:
                return repo_data
        
        raise HTTPException(status_code=404, detail=f"Repository '{owner_repo}' not found.")
    except FileNotFoundError:
        logging.error("config/repos.yaml not found", exc_info=True)
        raise HTTPException(status_code=404, detail="Repository configuration file not found.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config/repos.yaml: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error parsing repository configuration: {e}")

@app.post("/api/repo-context")
async def get_repository_context_endpoint(request_body: RepoContextRequest):
    """
    Fetches and returns the context of a given GitHub repository.
    """
    repo_url = request_body.repo_url
    logging.info(f"Received request for repository context for: {repo_url}")
    try:
        repo_context = get_repo_context(repo_url)
        if "Error" in repo_context.get("name", ""):
            raise HTTPException(status_code=500, detail=repo_context.get("description", "Failed to fetch repository context."))
        return repo_context
    except Exception as e:
        logging.error(f"Error fetching repository context for {repo_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error fetching repository context: {e}")

@app.post("/api/transcript")
async def post_transcript(request_body: TranscriptRequest):
    app_data = request_body.app.dict(exclude_unset=True) # Convert Pydantic model to dict, exclude optional fields not set
    app_name = app_data.get('name', 'unknown_app')
    logging.info(f"Received request for transcript generation for app: {app_name}")

    try:
        # generate_transcript now handles fetching from repo_url or url internally
        transcript, source_context, warning_message = await generate_transcript(app_data)
        response_data = {
            "transcript": transcript,
            "source_context": source_context
        }
        if warning_message:
            response_data["warning"] = warning_message
        return response_data
    except Exception as e:
        logging.error(f"Error generating transcript for app {app_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during transcript generation: {e}")

@app.post("/api/generate-mp3")
async def generate_mp3_endpoint(request_body: Mp3GenerateRequest):
    app_name = request_body.name
    transcript = request_body.transcript
    logging.info(f"Received request to generate MP3 for app: {app_name}")

    try:
        # Generate a unique base filename for the MP3
        filename_base = f"{app_name.lower().replace(' ', '_').replace('-', '_')}_{os.urandom(4).hex()}.mp3"
        
        # Call TTS agent. text_to_mp3 saves to its internal 'output' directory.
        # It returns the full path where it saved the file.
        full_local_mp3_path = text_to_mp3(transcript, filename_base)
        
        # Upload to GCS
        gcs_path = upload_to_gcs(full_local_mp3_path)

        # Clean up local file
        os.remove(full_local_mp3_path)
        logging.info(f"Cleaned up local MP3 file: {full_local_mp3_path}")

        return {
            "local_file_name": filename_base, # Return just the name for simplicity
            "gcs_path": gcs_path
        }
    except Exception as e:
        logging.error(f"Error generating or uploading MP3 for app {app_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during MP3 generation: {e}")

@app.post("/api/generate-video")
async def generate_video_endpoint():
    logging.info("Received request for video generation (not yet implemented).")
    return {"status": "not_implemented", "message": "Video generation will be added after MP3 flow works"}
