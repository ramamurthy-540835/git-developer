import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from orchestrator.langgraph_workflow import run_workflow
from agents.shared_github import fetch_user, list_repos, publish_readme

router = APIRouter(prefix='/api', tags=['readme'])

JOBS: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TokenRequest(BaseModel):
    github_token: str


class GenerateRequest(BaseModel):
    repo_url: str
    github_token: str


class PublishRequest(BaseModel):
    repo_url: str
    readme_markdown: str
    github_token: str
    branch: str = 'main'
    commit_message: str = 'docs: update README'
    pr_title: str = Field(default='docs: update README', max_length=100)
    pr_body: str = Field(default='Auto-generated README by git-developer', max_length=5000)


@router.post('/auth/token')
def auth_token(req: TokenRequest):
    try:
        user = fetch_user(req.github_token)
        return {'token_valid': True, 'user': {'login': user.get('login'), 'public_repos': user.get('public_repos', 0)}}
    except Exception as e:
        return {'token_valid': False, 'error': str(e)}


@router.post('/repos/list')
def repos_list(req: TokenRequest):
    try:
        repos = list_repos(req.github_token)
        return {'repos': repos}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _run_job(job_id: str, req: GenerateRequest):
    job = JOBS[job_id]
    try:
        job['status'] = 'running'
        job['events'].append({'stage': 'start', 'percent': 5, 'message': 'Starting workflow', 'ts': _now()})
        state = {
            'repo_url': req.repo_url,
            'github_token': req.github_token,
            'progress': [],
            'errors': [],
        }
        result = await asyncio.to_thread(run_workflow, state)
        for ev in result.get('progress', []):
            ev['ts'] = _now()
            job['events'].append(ev)
        payload = {
            'readme_markdown': result.get('readme_markdown', ''),
            'metrics': result.get('metrics', {}),
            'errors': result.get('errors', []),
        }
        job['result'] = payload
        job['status'] = 'completed'
        job['events'].append({'stage': 'done', 'percent': 100, 'message': 'Generation complete', 'ts': _now()})
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        job['events'].append({'stage': 'failed', 'percent': 100, 'message': str(e), 'ts': _now()})


@router.post('/generate-readme')
async def generate_readme(req: GenerateRequest):
    job_id = uuid4().hex
    JOBS[job_id] = {'status': 'queued', 'events': [], 'result': None, 'error': None, 'created_at': _now()}
    asyncio.create_task(_run_job(job_id, req))
    return {'job_id': job_id}


@router.get('/job-status/{job_id}')
async def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='job not found')
    events = job.get('events', [])
    last = events[-1] if events else {}
    return {
        'job_id': job_id,
        'status': job.get('status', 'queued'),
        'message': last.get('message', ''),
        'result': job.get('result'),
        'error': job.get('error'),
    }


@router.get('/generate-readme/{job_id}/stream')
async def stream_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail='job not found')

    async def event_generator():
        cursor = 0
        while True:
            job = JOBS.get(job_id)
            if not job:
                yield 'event: error\ndata: {"error":"job missing"}\n\n'
                return
            events = job.get('events', [])
            while cursor < len(events):
                data = events[cursor]
                cursor += 1
                yield f"data: {json.dumps(data)}\\n\\n"

            if job['status'] in ('completed', 'failed'):
                final_payload = {
                    'stage': 'result',
                    'status': job['status'],
                    'result': job.get('result'),
                    'error': job.get('error'),
                }
                yield f"data: {json.dumps(final_payload)}\\n\\n"
                return

            await asyncio.sleep(0.7)

    return StreamingResponse(event_generator(), media_type='text/event-stream')


@router.post('/publish-readme')
def publish_readme_endpoint(req: PublishRequest):
    try:
      pr_title = (req.pr_title or '').strip() or 'docs: update README'
      pr_body = (req.pr_body or '').strip() or 'Auto-generated README by git-developer'
      result = publish_readme(req.repo_url, req.readme_markdown, req.branch, req.commit_message, req.github_token, pr_title, pr_body)
      return {
          'success': True,
          'result': result,
          'pr_url': result.get('pr_url'),
          'pr_number': result.get('pr_number'),
          'pr_title': result.get('pr_title'),
      }
    except Exception as e:
      msg = str(e)
      if '404' in msg and 'ref' in msg:
          msg = 'Branch not found. Create it first.'
      if '401' in msg or '403' in msg:
          msg = 'Token invalid or expired'
      raise HTTPException(status_code=400, detail=msg)
