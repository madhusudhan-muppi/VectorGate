"""Model loading and confidence-based open-set rejection."""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .features import FEATURE_NAMES, feature_vector_from_detection, feature_vector_from_event

DEFAULT_ARTIFACT = Path(__file__).parent / "artifacts" / "vectorgate_demo_rf.pkl"
DEFAULT_METADATA = Path(__file__).parent / "artifacts" / "vectorgate_demo_rf.json"


@dataclass(frozen=True)
class ClassificationResult:
    predicted_class: str
    confidence: float | None
    model_version: str | None
    is_unknown: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DemoClassifier:
    """Cached Random Forest inference for the synthetic demonstration artifact."""

    def __init__(self, artifact_path: Path | None = None, metadata_path: Path | None = None):
        self.artifact_path = artifact_path or Path(os.getenv("VECTORGATE_CLASSIFIER_ARTIFACT", DEFAULT_ARTIFACT))
        self.metadata_path = metadata_path or Path(os.getenv("VECTORGATE_CLASSIFIER_METADATA", DEFAULT_METADATA))
        self.model: Any | None = None
        self.metadata: dict[str, Any] | None = None
        self.load_error: str | None = None
        self._load_once()

    def _load_once(self) -> None:
        try:
            with self.artifact_path.open("rb") as handle:
                model = pickle.load(handle)
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if tuple(metadata.get("feature_names", ())) != FEATURE_NAMES:
                raise ValueError("artifact feature schema does not match the runtime schema")
            if metadata.get("training_data_type") != "synthetic_demo":
                raise ValueError("artifact training data type is not synthetic_demo")
            self.model = model
            self.metadata = metadata
        except Exception as error:  # An unavailable optional classifier must not stop ingestion.
            self.load_error = str(error)

    @property
    def loaded(self) -> bool:
        return self.model is not None and self.metadata is not None

    def classify_values(self, values: Mapping[str, float | int | None]) -> ClassificationResult:
        if not self.loaded:
            return ClassificationResult("UNKNOWN", None, None, True, "classifier artifact unavailable")
        try:
            vector = feature_vector_from_detection(values)
        except (TypeError, ValueError) as error:
            return ClassificationResult("UNKNOWN", None, self.metadata.get("model_version"), True, str(error))
        if vector[6] < 5.0:
            return ClassificationResult("UNKNOWN", None, self.metadata.get("model_version"), True, "insufficient estimated SNR")
        probabilities = self.model.predict_proba(vector.reshape(1, -1))[0]
        best_index = int(np.argmax(probabilities))
        confidence = float(probabilities[best_index])
        threshold = float(self.metadata["unknown_threshold"])
        if confidence < threshold:
            return ClassificationResult("UNKNOWN", confidence, self.metadata["model_version"], True, "model confidence below unknown threshold")
        return ClassificationResult(str(self.model.classes_[best_index]), confidence, self.metadata["model_version"], False, "confidence threshold met")

    def classify_event(self, event) -> ClassificationResult:
        try:
            values = event.features.as_dict()
            values["event_duration_seconds"] = event.duration_seconds
            return self.classify_values(values)
        except (TypeError, ValueError) as error:
            return ClassificationResult("UNKNOWN", None, self.metadata.get("model_version") if self.metadata else None, True, str(error))

    def status(self) -> dict[str, Any]:
        metadata = self.metadata or {}
        return {
            "enabled": os.getenv("VECTORGATE_CLASSIFIER_ENABLED", "0").lower() in {"1", "true", "yes", "on"},
            "loaded": self.loaded,
            "model_version": metadata.get("model_version"),
            "model_type": metadata.get("model_type"),
            "training_data_type": metadata.get("training_data_type"),
            "unknown_threshold": metadata.get("unknown_threshold"),
            "classes": metadata.get("class_names", []),
            "synthetic_validation_metrics": metadata.get("synthetic_validation_metrics"),
            "load_error": self.load_error,
        }


def classifier_status() -> dict[str, Any]:
    return DemoClassifier().status()
