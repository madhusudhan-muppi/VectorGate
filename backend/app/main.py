"""FastAPI application entry point for the VectorGate prototype backend."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import configure_database, init_db
from .routes import classifier, detections, health, nodes, species, stats


def create_app(database_url: str | None = None) -> FastAPI:
    if database_url is not None:
        configure_database(database_url)
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_db()
        yield

    app = FastAPI(
        title="VectorGate API",
        version="0.3.0",
        lifespan=lifespan,
        description=(
            "Prototype API for VectorGate optical sensing nodes and DSP detections. "
            "Detection frequencies are raw signal features, not medically validated species identification."
        ),
    )
    origins = [
        origin.strip()
        for origin in os.getenv(
            "VECTORGATE_CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(nodes.router, prefix="/api/v1")
    app.include_router(detections.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")
    app.include_router(classifier.router, prefix="/api/v1")
    app.include_router(species.router, prefix="/api/v1")

    return app


app = create_app()
