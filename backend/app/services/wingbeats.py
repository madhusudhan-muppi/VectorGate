"""Cached WINGBEATS classifier service for API ingestion.

Kept separate from :mod:`backend.app.services.classifier`, which serves the
synthetic demo artifact against the 8-feature detection contract. This one
classifies from a raw sample batch, because the WINGBEATS model needs 25
features that a detection payload does not carry.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from software.wingbeats.classifier import WingbeatsClassifier

_classifier: WingbeatsClassifier | None = None


def wingbeats_enabled() -> bool:
    return os.getenv("VECTORGATE_WINGBEATS_ENABLED", "0").lower() in {"1", "true", "yes", "on"}


def get_wingbeats_classifier() -> WingbeatsClassifier:
    global _classifier
    if _classifier is None:
        _classifier = WingbeatsClassifier()
    return _classifier


def reset_wingbeats_classifier() -> None:
    """Drop the cached instance so a new artifact or threshold is picked up."""
    global _classifier
    _classifier = None


def classify_samples(samples: list[float], sample_rate_hz: float) -> dict[str, Any] | None:
    """Classify a waveform, or return ``None`` when the model is not serving."""
    if not wingbeats_enabled():
        return None
    result = get_wingbeats_classifier().classify_samples(np.asarray(samples, dtype=float), sample_rate_hz)
    return {
        "predicted_class": result.predicted_class,
        "confidence": result.confidence,
        "model_version": result.model_version,
    }


def wingbeats_status() -> dict[str, Any]:
    status = get_wingbeats_classifier().status()
    status["enabled"] = wingbeats_enabled()
    return status
