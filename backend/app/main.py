from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, projects, scripts, scenes, prompts, assets, audio, subtitles, renders, providers
from app.core.storage import init_storage
from app.core.database import Base, engine, SessionLocal
from app.services import model_catalog_service

# Initialize database
Base.metadata.create_all(bind=engine)

# Seed default models
db = SessionLocal()
try:
    model_catalog_service.seed_default_mock_models(db)
finally:
    db.close()

# Initialize storage
init_storage()

app = FastAPI(title="AI 3D Explainer Shorts Generator API")

# Configure CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(scripts.router, prefix="/api", tags=["scripts"])
app.include_router(scenes.router, prefix="/api", tags=["scenes"])
app.include_router(prompts.router, prefix="/api", tags=["prompts"])
app.include_router(assets.router, prefix="/api", tags=["assets"])
app.include_router(audio.router, prefix="/api", tags=["audio"])
app.include_router(subtitles.router, prefix="/api", tags=["subtitles"])
app.include_router(renders.router, prefix="/api", tags=["renders"])
app.include_router(providers.router, prefix="/api", tags=["providers"])
