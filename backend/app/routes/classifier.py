"""Classifier readiness/status endpoints."""

from fastapi import APIRouter

from ..services.classifier import classifier_status
from ..services.wingbeats import wingbeats_status

router = APIRouter(tags=["classifier"])


@router.get("/classifier/status")
def get_classifier_status() -> dict:
    """Status of the classifier serving the dashboard.

    The WINGBEATS model takes precedence when it is enabled, since ingestion
    prefers it whenever a payload carries a sample batch. The synthetic demo
    artifact stays reachable under ``demo`` so the older path remains visible.
    """
    demo = classifier_status()
    wingbeats = wingbeats_status()
    if wingbeats.get("enabled") and wingbeats.get("loaded"):
        return {**wingbeats, "demo": demo}
    return {**demo, "wingbeats": wingbeats}


@router.get("/classifier/wingbeats")
def get_wingbeats_status() -> dict:
    return wingbeats_status()
