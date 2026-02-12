"""
QUEL Light - Stage Node Backend Server
FastAPI server for 2D → 3D conversion using Meta SAM 3D
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

from routers import stage_node

# Create FastAPI app
app = FastAPI(
    title="QUEL Stage Node API",
    description="2D → 3D conversion API using Meta SAM 3D",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://quel.ai",
        "https://*.quel.ai",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create storage directories
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "uploads").mkdir(exist_ok=True)
(STORAGE_DIR / "models").mkdir(exist_ok=True)
(STORAGE_DIR / "renders").mkdir(exist_ok=True)

# Mount static files for serving 3D models
app.mount("/models", StaticFiles(directory=str(STORAGE_DIR / "models")), name="models")
app.mount("/renders", StaticFiles(directory=str(STORAGE_DIR / "renders")), name="renders")

# Include routers
app.include_router(stage_node.router, prefix="/api/stage", tags=["stage"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "QUEL Stage Node API",
        "version": "1.0.0",
        "endpoints": {
            "convert": "POST /api/stage/convert",
            "render": "POST /api/stage/render",
            "model": "GET /models/{model_id}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "storage": {
            "uploads": os.path.exists(STORAGE_DIR / "uploads"),
            "models": os.path.exists(STORAGE_DIR / "models"),
            "renders": os.path.exists(STORAGE_DIR / "renders"),
        }
    }

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Remove in production
        log_level="info"
    )