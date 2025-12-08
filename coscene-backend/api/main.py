"""
FastAPI application entry point for CoScene Backend.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from api.config import get_settings
from api.models import HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting CoScene Backend...")
    logger.info(f"Database URL: {settings.database_url.split('@')[1]}")  # Hide credentials
    logger.info(f"Debug mode: {settings.debug}")

    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Load LangGraph agent

    yield

    # Shutdown
    logger.info("Shutting down CoScene Backend...")
    # TODO: Close database connections
    # TODO: Close Redis connections


# Create FastAPI application
app = FastAPI(
    title="CoScene API",
    description="Agentic 3D Scene Editing Backend with LangGraph and USD",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Check Endpoints ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Liveness probe - check if service is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        checks={"api": True},
    )


@app.get("/ready", response_model=HealthResponse)
async def readiness_check():
    """
    Readiness probe - check if service can handle traffic.
    """
    checks = {
        "api": True,
        "database": False,  # TODO: Check database connection
        "redis": False,  # TODO: Check Redis connection
    }

    all_ready = all(checks.values())
    status = "healthy" if all_ready else "degraded"

    return HealthResponse(
        status=status,
        timestamp=datetime.now(),
        checks=checks,
    )


@app.get("/")
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "name": "CoScene API",
        "version": "0.1.0",
        "description": "Agentic 3D Scene Editing Backend",
        "docs": "/docs",
        "health": "/health",
    }


# ============ Include Routers ============
from api.routes import sessions, scenes, websocket

app.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
app.include_router(scenes.router, prefix="/sessions", tags=["Scenes"])
app.include_router(websocket.router, tags=["WebSocket"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
