"""Stable model feature schema shared by training and inference."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from software.data.models import FlightEventResult

FEATURE_NAMES = (
    "dominant_frequency_hz",
    "second_harmonic_ratio",
    "third_harmonic_ratio",
    "rms",
    "peak_to_peak",
    "spectral_energy",
    "estimated_snr_db",
    "event_duration_seconds",
)


def _vector(values: Mapping[str, float | int | None]) -> np.ndarray:
    missing = [name for name in FEATURE_NAMES if values.get(name) is None]
    if missing:
        raise ValueError(f"missing required classifier features: {', '.join(missing)}")
    result = np.asarray([float(values[name]) for name in FEATURE_NAMES], dtype=float)
    if result.shape != (len(FEATURE_NAMES),) or not np.all(np.isfinite(result)):
        raise ValueError("classifier features must be finite")
    return result


def feature_vector_from_event(event: FlightEventResult) -> np.ndarray:
    values = event.features.as_dict()
    values["event_duration_seconds"] = event.duration_seconds
    return _vector(values)


def feature_vector_from_detection(values: Mapping[str, float | int | None]) -> np.ndarray:
    return _vector(values)
