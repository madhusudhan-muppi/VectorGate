"""Optional cached classifier service for API ingestion."""

from __future__ import annotations

import os
from typing import Any

from software.classifier.model import DemoClassifier

_classifier: DemoClassifier | None = None


def classifier_enabled() -> bool:
    return os.getenv("VECTORGATE_CLASSIFIER_ENABLED", "0").lower() in {"1", "true", "yes", "on"}


def get_classifier() -> DemoClassifier:
    global _classifier
    if _classifier is None:
        _classifier = DemoClassifier()
    return _classifier


def classify_detection(values: dict[str, Any]) -> dict[str, Any] | None:
    if not classifier_enabled():
        return None
    result = get_classifier().classify_values(values)
    return {
        "predicted_class": result.predicted_class,
        "confidence": result.confidence,
        "model_version": result.model_version,
    }


def classifier_status() -> dict[str, Any]:
    status = get_classifier().status()
    status["enabled"] = classifier_enabled()
    return status
