"""Classifier readiness/status endpoint."""

from fastapi import APIRouter

from ..services.classifier import classifier_status

router = APIRouter(tags=["classifier"])


@router.get("/classifier/status")
def get_classifier_status() -> dict:
    return classifier_status()
