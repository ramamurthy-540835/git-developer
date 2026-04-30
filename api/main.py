import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.readme_routes import router as readme_router

load_dotenv(dotenv_path='./.env.local')

app = FastAPI(title='git-developer README Agent API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return {'ok': True, 'service': 'git-developer-readme-api'}


app.include_router(readme_router)
