import os
import asyncio
import logging
import yaml
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from uuid import uuid4
from pathlib import Path

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
from agents.sharepoint_uploader import upload_to_sharepoint
from agents.video_agent import mp3_to_video
from agents.scene_planner import generate_scene_plan
from google import genai
from google.genai import types as genai_types


# Initialize FastAPI app
app = FastAPI(title="GCP Studio Media Agent")

# Pydantic model for repo context request
class RepoContextRequest(BaseModel):
    repo_url: str

# Add CORS middleware
origins = [
    os.getenv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:3000"),
    os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000"),
    os.getenv("NEXT_PUBLIC_BACKEND_URL", "http://localhost:3000"),
    # Add any other origins you need to allow
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development, refine in production
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

class VideoGenerateRequest(BaseModel):
    name: str
    transcript: str
    repo_context: Optional[Dict[str, Any]] = None
    scene_plan: Optional[List[Dict[str, Any]]] = None
    use_scene_plan: Optional[bool] = True
    renderer_mode: Optional[str] = "local_ffmpeg"
    video_prompt: Optional[str] = None
    duration_seconds: Optional[int] = 32
    upload_to_sharepoint: Optional[bool] = True # New field for controlling SharePoint upload

class ScenePlanRequest(BaseModel):
    repo_url: str
    product_name: str
    architecture_mmd: Optional[str] = None

def _compact_prompt_from_scene_plan(scene_plan: List[Dict[str, Any]]) -> str:
    chunks = []
    for i, s in enumerate(scene_plan[:4], start=1):
        beat = (s.get("beat") or f"scene_{i}").strip()
        title = (s.get("title") or f"Scene {i}").strip()
        caption = (s.get("caption") or "").strip()
        diagram = (s.get("mermaid_diagram") or s.get("diagram") or "").strip().replace("\n", " ")
        chunks.append(f"Scene {i} ({beat}): {title} - {caption}. [show Mermaid: {diagram}]")
    return " ".join(chunks)

VIDEO_JOBS: Dict[str, Dict[str, Any]] = {}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def update_job(job_id: str, **kwargs):
    if job_id in VIDEO_JOBS:
        VIDEO_JOBS[job_id].update(kwargs)
        VIDEO_JOBS[job_id]["updated_at"] = now_iso()

async def run_video_job(job_id: str, app_name: str, transcript: str, repo_context: Optional[Dict[str, Any]] = None, upload_to_sharepoint_flag: bool = True):
    mp3_path = None
    mp4_path = None
    sharepoint_upload_status = "skipped"
    sharepoint_upload_error = None
    sharepoint_url = None

    try:
        update_job(job_id, status="generating_mp3", message="Generating narration audio")
        mp3_name = f"{app_name.lower().replace(' ', '_').replace('-', '_')}_{uuid4().hex[:8]}.mp3"
        mp3_path = await asyncio.wait_for(asyncio.to_thread(text_to_mp3, transcript, mp3_name), timeout=120)

        update_job(job_id, status="uploading_mp3", message="Uploading MP3 to storage")
        mp3_gcs = await asyncio.wait_for(asyncio.to_thread(upload_to_gcs, mp3_path), timeout=120)

        update_job(job_id, status="rendering_video", message="Rendering MP4 from narration")
        mp4_name = mp3_name.replace(".mp3", ".mp4")
        mp4_path = await asyncio.wait_for(
            asyncio.to_thread(mp3_to_video, mp3_path, mp4_name, app_name, transcript, repo_context),
            timeout=180
        )

        update_job(job_id, status="uploading_video", message="Uploading MP4 to storage")
        mp4_gcs = await asyncio.wait_for(asyncio.to_thread(upload_to_gcs, mp4_path), timeout=120)

        if upload_to_sharepoint_flag:
            sharepoint_webhook_url = os.environ.get("SHAREPOINT_WEBHOOK_URL")
            if sharepoint_webhook_url and mp4_path:
                try:
                    logging.info(f"SharePoint: Starting upload for {os.path.basename(mp4_path)}...")
                    description = f"Generated media demo for {app_name}" # Use a more explicit description
                    sharepoint_result = await asyncio.wait_for(
                        asyncio.to_thread(upload_to_sharepoint, mp4_path, app_name, description),
                        timeout=300
                    )
                    sharepoint_url = (sharepoint_result or {}).get("sharepoint_link")
                    sharepoint_upload_status = "uploaded"
                    sharepoint_upload_error = None
                    logging.info(f"SharePoint: Upload completed successfully to {sharepoint_url}")
                except ValueError as e:
                    sharepoint_upload_status = "failed"
                    sharepoint_upload_error = str(e)
                    logging.warning(f"SharePoint: Upload skipped for {app_name} due to configuration error: {e}")
                except Exception as e:
                    sharepoint_upload_status = "failed"
                    sharepoint_upload_error = str(e)
                    logging.warning(f"SharePoint: Failed to upload {os.path.basename(mp4_path)}: {e}", exc_info=True)
            else:
                sharepoint_upload_status = "skipped"
                sharepoint_upload_error = "SHAREPOINT_WEBHOOK_URL not set or MP4 path missing."
                logging.info("SharePoint: SHAREPOINT_WEBHOOK_URL not set or MP4 path missing. Skipping SharePoint upload.")
        else:
            logging.info("SharePoint: Upload to SharePoint explicitly skipped by request.")

        update_job(
            job_id,
            status="completed",
            message="Video generation completed",
            result={
                "mp3_file_name": os.path.basename(mp3_path),
                "mp3_local_path": mp3_path,
                "mp3_gcs_path": mp3_gcs,
                "video_file_name": os.path.basename(mp4_path),
                "video_local_path": mp4_path,
                "video_gcs_path": mp4_gcs,
                "sharepoint_status": sharepoint_upload_status,
                "sharepoint_url": sharepoint_url,
                "sharepoint_error": sharepoint_upload_error,
            },
            completed_at=now_iso(),
        )
    except asyncio.TimeoutError:
        update_job(job_id, status="failed", message="Job timed out", error="Timeout during media generation/upload")
    except Exception as e:
        logging.error(f"Video job failed for {app_name}: {e}", exc_info=True)
        update_job(job_id, status="failed", message="Job failed", error=str(e))
    finally:
        for local_path in [mp3_path, mp4_path]:
            try:
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)
            except Exception:
                pass

def _default_video_prompt(name: str, transcript: str, repo_context: Optional[Dict[str, Any]]) -> str:
    desc = (repo_context or {}).get("description") or ""
    tech = ", ".join((repo_context or {}).get("tech_stack") or [])
    return (
        f"Create a cinematic product demo for {name}. "
        f"Show real workflow, UI actions, and business impact. "
        f"Context: {desc}. Tech cues: {tech}. "
        f"Narration basis: {transcript[:1200]}"
    )

async def run_veo_job(job_id: str, app_name: str, video_prompt: str, duration_seconds: int, transcript: str, repo_context: Optional[Dict[str, Any]] = None, upload_to_sharepoint_flag: bool = True):
    output_mp4_path = None
    sharepoint_upload_status = "skipped"
    sharepoint_upload_error = None
    sharepoint_url = None

    try:
        update_job(job_id, status="rendering_video", message="Generating video with Veo Lite")
        client = genai.Client(vertexai=True, project="ctoteam", location="us-central1")
        source = genai_types.GenerateVideosSource(prompt=video_prompt)
        config = genai_types.GenerateVideosConfig(
            aspect_ratio="16:9",
            number_of_videos=1,
            duration_seconds=duration_seconds,
            person_generation="allow_all",
            generate_audio=True,
            resolution="720p",
            seed=0,
        )
        operation = client.models.generate_videos(
            model="veo-3.1-lite-generate-001", source=source, config=config
        )
        while not operation.done:
            await asyncio.sleep(5)
            operation = client.operations.get(operation)

        response = operation.result
        generated = (response.generated_videos if response else None) or []
        if not generated or not generated[0].video:
            logging.error(
                "Veo returned no videos. op_done=%s op_name=%s response_type=%s",
                getattr(operation, "done", None),
                getattr(operation, "name", None),
                type(response).__name__ if response else None,
            )
            update_job(
                job_id,
                status="fallback_local",
                message="Veo returned no video; falling back to local FFmpeg renderer",
            )
            mp3_name = f"{app_name.lower().replace(' ', '_').replace('-', '_')}_{uuid4().hex[:8]}.mp3"
            mp3_path = await asyncio.wait_for(asyncio.to_thread(text_to_mp3, transcript, mp3_name), timeout=120)
            mp4_name = mp3_name.replace(".mp3", ".mp4")
            mp4_path = await asyncio.wait_for(
                asyncio.to_thread(mp3_to_video, mp3_path, mp4_name, app_name, transcript, repo_context),
                timeout=180,
            )
            mp3_gcs = await asyncio.wait_for(asyncio.to_thread(upload_to_gcs, mp3_path), timeout=120)
            mp4_gcs = await asyncio.wait_for(asyncio.to_thread(upload_to_gcs, mp4_path), timeout=120)
            update_job(
                job_id,
                status="completed",
                message="Veo returned no video; completed with local FFmpeg fallback",
                result={
                    "renderer_mode": "local_ffmpeg_fallback",
                    "video_prompt": video_prompt,
                    "estimated_cost_usd": round(duration_seconds * 0.05, 4),
                    "mp3_file_name": os.path.basename(mp3_path),
                    "mp3_local_path": str(mp3_path),
                    "mp3_gcs_path": mp3_gcs,
                    "video_file_name": os.path.basename(mp4_path),
                    "video_local_path": str(mp4_path),
                    "video_gcs_path": mp4_gcs,
                    "veo_operation_name": getattr(operation, "name", None),
                    "sharepoint_status": sharepoint_upload_status, # Still add status for consistency
                    "sharepoint_url": sharepoint_url,
                    "sharepoint_error": sharepoint_upload_error,
                },
                completed_at=now_iso(),
            )
            return

        update_job(job_id, status="saving_video", message="Saving Veo output locally")
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_mp4_path = output_dir / f"{app_name.lower().replace(' ', '_')}_{uuid4().hex[:8]}_veo.mp4"
        generated[0].video.save(str(output_mp4_path))

        update_job(job_id, status="uploading_video", message="Uploading MP4 to storage")
        mp4_gcs = await asyncio.wait_for(asyncio.to_thread(upload_to_gcs, str(output_mp4_path)), timeout=180)
        
        if upload_to_sharepoint_flag:
            sharepoint_webhook_url = os.environ.get("SHAREPOINT_WEBHOOK_URL")
            if sharepoint_webhook_url and output_mp4_path:
                try:
                    logging.info(f"SharePoint: Starting upload for {output_mp4_path.name} (Veo job)...")
                    description = f"Generated media demo for {app_name}" # Use a more explicit description
                    sharepoint_result = await asyncio.wait_for(
                        asyncio.to_thread(upload_to_sharepoint, str(output_mp4_path), app_name, description),
                        timeout=300
                    )
                    sharepoint_url = (sharepoint_result or {}).get("sharepoint_link")
                    sharepoint_upload_status = "uploaded"
                    sharepoint_upload_error = None
                    logging.info(f"SharePoint: Upload completed successfully to {sharepoint_url} (Veo job).")
                except ValueError as e:
                    sharepoint_upload_status = "failed"
                    sharepoint_upload_error = str(e)
                    logging.warning(f"SharePoint: Upload skipped for {app_name} (Veo job) due to configuration error: {e}")
                except Exception as e:
                    sharepoint_upload_status = "failed"
                    sharepoint_upload_error = str(e)
                    logging.warning(f"SharePoint: Failed to upload {output_mp4_path.name} (Veo job): {e}", exc_info=True)
            else:
                sharepoint_upload_status = "skipped"
                sharepoint_upload_error = "SHAREPOINT_WEBHOOK_URL not set or MP4 path missing."
                logging.info("SharePoint: SHAREPOINT_WEBHOOK_URL not set or MP4 path missing. Skipping SharePoint upload (Veo job).")
        else:
            logging.info("SharePoint: Upload to SharePoint explicitly skipped by request (Veo job).")

        update_job(
            job_id,
            status="completed",
            message="Video generation completed",
            result={
                "renderer_mode": "veo_lite",
                "video_prompt": video_prompt,
                "estimated_cost_usd": round(duration_seconds * 0.05, 4),
                "duration_seconds": duration_seconds,
                "video_file_name": output_mp4_path.name,
                "video_local_path": str(output_mp4_path),
                "video_gcs_path": mp4_gcs,
                "sharepoint_status": sharepoint_upload_status,
                "sharepoint_url": sharepoint_url,
                "sharepoint_error": sharepoint_upload_error,
            },
            completed_at=now_iso(),
        )
    except Exception as e:
        logging.error(f"Veo job failed for {app_name}: {e}", exc_info=True)
        update_job(job_id, status="failed", message="Job failed", error=str(e))

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
        repos = repos_config.get("repos", [])
        logging.info(f"Loaded {len(repos)} repos from config/repos.yaml")
        return {"repos": repos}
    except FileNotFoundError:
        error_msg = "config/repos.yaml not found. Please ensure the repository configuration file exists at the project root."
        logging.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)
    except yaml.YAMLError as e:
        error_msg = f"Error parsing config/repos.yaml: {e}. Please check the YAML file for syntax errors."
        logging.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

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


@app.post("/api/scene-plan")
async def post_scene_plan(request_body: ScenePlanRequest):
    try:
        plan = await asyncio.wait_for(
            asyncio.to_thread(
                generate_scene_plan,
                request_body.repo_url,
                request_body.product_name,
                request_body.architecture_mmd,
            ),
            timeout=120,
        )
        scenes = plan.get("scenes", [])
        return {
            "success": True,
            "scenes": scenes,
            "specificity_score": plan.get("specificity_score", 0),
            "scene_diagnostics": plan.get("scene_diagnostics", []),
            "topics": plan.get("topics", {}),
        }
    except Exception as e:
        logging.error(f"Scene plan generation failed: {e}", exc_info=True)
        return {"success": False, "error": f"{e}"}

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
        logging.info(f"MP3 step: validate transcript for {app_name}")
        if not transcript or not transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript is empty. Generate or enter transcript text first.")

        # Generate a unique base filename for the MP3
        filename_base = f"{app_name.lower().replace(' ', '_').replace('-', '_')}_{os.urandom(4).hex()}.mp3"

        # Run network-bound calls in worker threads with explicit timeouts.
        logging.info(f"MP3 step: tts start for {app_name}")
        full_local_mp3_path = await asyncio.wait_for(
            asyncio.to_thread(text_to_mp3, transcript, filename_base),
            timeout=120
        )
        logging.info(f"MP3 step: upload start for {app_name}")
        gcs_path = await asyncio.wait_for(
            asyncio.to_thread(upload_to_gcs, full_local_mp3_path),
            timeout=120
        )

        # Clean up local file
        os.remove(full_local_mp3_path)
        logging.info(f"Cleaned up local MP3 file: {full_local_mp3_path}")

        return {
            "local_file_name": filename_base, # Return just the name for simplicity
            "local_path": full_local_mp3_path,
            "gcs_path": gcs_path
        }
    except asyncio.TimeoutError:
        logging.error(f"Timeout generating or uploading MP3 for app {app_name}", exc_info=True)
        raise HTTPException(status_code=504, detail="MP3 generation timed out. Please retry.")
    except Exception as e:
        logging.error(f"Error generating or uploading MP3 for app {app_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during MP3 generation: {e}")

@app.post("/api/generate-video")
async def generate_video_endpoint(request_body: VideoGenerateRequest):
    app_name = request_body.name
    transcript = request_body.transcript
    repo_context = request_body.repo_context
    scene_plan = request_body.scene_plan or []
    use_scene_plan = request_body.use_scene_plan if request_body.use_scene_plan is not None else True
    renderer_mode = request_body.renderer_mode or "local_ffmpeg"
    duration_seconds = max(8, min(60, int(request_body.duration_seconds or 32)))

    if use_scene_plan:
        if not scene_plan:
            raise HTTPException(status_code=400, detail="Use Scene Plan enabled but no scene_plan provided.")
        scene_captions = [str(s.get("caption", "")).strip() for s in scene_plan[:4]]
        if any(not c for c in scene_captions):
            raise HTTPException(status_code=400, detail="Each scene must include a non-empty caption.")
        transcript = ". ".join(scene_captions)
        video_prompt = _compact_prompt_from_scene_plan(scene_plan)
        if isinstance(repo_context, dict):
            repo_context = {**repo_context, "scene_plan": scene_plan}
    else:
        video_prompt = request_body.video_prompt or _default_video_prompt(app_name, transcript, repo_context)

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty. Generate or enter transcript text first.")

    job_id = uuid4().hex
    VIDEO_JOBS[job_id] = {
        "job_id": job_id,
        "name": app_name,
        "status": "queued",
        "message": "Job accepted",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "result": None,
        "error": None,
        "renderer_mode": renderer_mode,
        "video_prompt": video_prompt,
        "estimated_cost_usd": round(duration_seconds * 0.05, 4) if renderer_mode == "veo_lite" else 0.0,
        "duration_seconds": duration_seconds,
    }
    upload_to_sharepoint_flag = request_body.upload_to_sharepoint if request_body.upload_to_sharepoint is not None else True

    if renderer_mode == "veo_lite":
        asyncio.create_task(run_veo_job(job_id, app_name, video_prompt, duration_seconds, transcript, repo_context, upload_to_sharepoint_flag))
    else:
        asyncio.create_task(run_video_job(job_id, app_name, transcript, repo_context, upload_to_sharepoint_flag))
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = VIDEO_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
