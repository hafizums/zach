from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import health, projects, scripts
from app.core.storage import init_storage
from app.core.database import Base, engine

# Initialize database
Base.metadata.create_all(bind=engine)

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
