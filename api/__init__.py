"""Expose FastAPI application for ``uvicorn api:app`` entrypoint."""

from .app import app

__all__ = ["app"]
