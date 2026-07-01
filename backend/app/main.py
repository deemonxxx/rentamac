"""RentaMac Backend — FastAPI Application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import clients, nodes, rustdesk, webhooks
from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    logger.info("RentaMac backend starting up...")
    yield
    logger.info("RentaMac backend shutting down...")
    await engine.dispose()


app = FastAPI(
    title="RentaMac API",
    description="Backend API for the RentaMac macOS rental platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(nodes.router)
app.include_router(clients.router)
app.include_router(rustdesk.router)
app.include_router(webhooks.router)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict:
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok", "service": "rentamac-api", "version": "1.0.0"}
