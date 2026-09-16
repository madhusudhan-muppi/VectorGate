"""Serve the WINGBEATS species model with explicit open-set rejection.

The model is trained on 8 kHz optical recordings. A node sampling at some other
rate produces different values for every rate-sensitive feature -- zero-crossing
rate, spectral rolloff, the bioacoustic band ratios -- so incoming waveforms are
resampled to the training rate before extraction rather than being fed in at
whatever rate they arrived at.

Features are computed by :mod:`software.wingbeats.features`, the same module
training uses. That is deliberate: it removes the possibility of the serving
features drifting from the trained ones.

Everything below the confidence threshold is reported as Unknown. The threshold
is stored in the artifact and can be raised at deploy time; on the session-
grouped evaluation, 0.70 buys 91% accuracy on 35% of passages while the saved
default of ~0.37 gives 72% accuracy on 90% of them.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import resample_poly

from .features import extract_from_samples, scale_invariant_names

DEFAULT_ARTIFACT = Path("data/vectorgate_wingbeats_rf.joblib")
TRAINING_SAMPLE_RATE_HZ = 8000.0
MAX_RESAMPLE_DENOMINATOR = 1000


@dataclass(frozen=True)
class WingbeatsClassification:
    predicted_class: str
    confidence: float | None
    model_version: str | None
    is_unknown: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unknown(reason: str, version: str | None = None, confidence: float | None = None) -> WingbeatsClassification:
    return WingbeatsClassification("UNKNOWN", confidence, version, True, reason)


class WingbeatsClassifier:
    """Cached inference over the WINGBEATS-trained random forest."""

    def __init__(self, artifact_path: Path | None = None, threshold: float | None = None):
        self.artifact_path = Path(
            artifact_path or os.getenv("VECTORGATE_WINGBEATS_ARTIFACT", DEFAULT_ARTIFACT)
        )
        self.bundle: dict[str, Any] | None = None
        self.load_error: str | None = None
        self._threshold_override = threshold
        self._load_once()

    def _load_once(self) -> None:
        try:
            import joblib

            bundle = joblib.load(self.artifact_path)
            missing = [key for key in ("model", "columns", "classes") if key not in bundle]
            if missing:
                raise ValueError(f"artifact is missing keys: {', '.join(missing)}")
            expected = set(scale_invariant_names())
            if not set(bundle["columns"]).issubset(expected):
                raise ValueError("artifact columns do not match the runtime feature schema")
            self.bundle = bundle
        except Exception as error:  # An unavailable model must not stop ingestion.
            self.load_error = str(error)

    @property
    def loaded(self) -> bool:
        return self.bundle is not None

    @property
    def threshold(self) -> float:
        if self._threshold_override is not None:
            return self._threshold_override
        override = os.getenv("VECTORGATE_WINGBEATS_THRESHOLD")
        if override:
            try:
                return float(override)
            except ValueError:
                pass
        return float((self.bundle or {}).get("unknown_threshold", 0.5))

    @property
    def training_sample_rate(self) -> float:
        return float((self.bundle or {}).get("training_sample_rate_hz", TRAINING_SAMPLE_RATE_HZ))

    def _resample(self, samples: np.ndarray, sample_rate: float) -> np.ndarray:
        target = self.training_sample_rate
        if abs(sample_rate - target) < 1e-6:
            return samples
        ratio = Fraction(target / sample_rate).limit_denominator(MAX_RESAMPLE_DENOMINATOR)
        return resample_poly(samples, ratio.numerator, ratio.denominator)

    def classify_samples(self, samples: np.ndarray, sample_rate: float) -> WingbeatsClassification:
        if not self.loaded:
            return _unknown("wingbeats artifact unavailable")
        version = str(self.bundle.get("model_version", "vectorgate-wingbeats-rf-v1"))
        if sample_rate <= 0:
            return _unknown("sample_rate_hz must be positive", version)

        array = np.asarray(samples, dtype=np.float64)
        if array.size == 0 or not np.all(np.isfinite(array)):
            return _unknown("samples must be finite and non-empty", version)

        try:
            resampled = self._resample(array, sample_rate)
            features = extract_from_samples(resampled, self.training_sample_rate)
        except Exception as error:
            return _unknown(f"feature extraction failed: {error}", version)
        if features is None:
            return _unknown("waveform too short or silent for feature extraction", version)

        columns = self.bundle["columns"]
        try:
            # A named frame, not a bare array: sklearn then verifies the column
            # names against the fitted ones, so a reordered feature set fails
            # loudly instead of silently scoring the wrong values.
            vector = pd.DataFrame([[features[name] for name in columns]], columns=columns)
        except KeyError as error:
            return _unknown(f"missing feature {error}", version)

        probabilities = self.bundle["model"].predict_proba(vector)[0]
        best = int(np.argmax(probabilities))
        confidence = float(probabilities[best])
        if confidence < self.threshold:
            return _unknown("model confidence below unknown threshold", version, confidence)
        label = str(self.bundle["model"].classes_[best])
        return WingbeatsClassification(label, confidence, version, False, "confidence threshold met")

    def status(self) -> dict[str, Any]:
        bundle = self.bundle or {}
        return {
            "loaded": self.loaded,
            "model_version": bundle.get("model_version", "vectorgate-wingbeats-rf-v1" if self.loaded else None),
            "model_type": type(bundle["model"]).__name__ if self.loaded else None,
            "training_data_type": "wingbeats_optical",
            "dataset": bundle.get("dataset"),
            "split": bundle.get("split"),
            "session_grouped_accuracy": bundle.get("session_grouped_accuracy"),
            "unknown_threshold": self.threshold if self.loaded else None,
            "training_sample_rate_hz": self.training_sample_rate if self.loaded else None,
            "feature_set": bundle.get("feature_set"),
            "n_features": len(bundle.get("columns", [])) or None,
            "classes": list(bundle.get("classes", [])),
            "validation_note": (
                "Session-grouped accuracy on a public optical dataset. "
                "Cross-sensor validation on VectorGate hardware is outstanding; "
                "this is not medically validated species identification."
            ),
            "load_error": self.load_error,
        }
