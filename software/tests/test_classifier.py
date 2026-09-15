"""Deterministic tests for synthetic classification and UNKNOWN rejection."""

import json

import numpy as np
import pytest

from software.classifier.features import FEATURE_NAMES, feature_vector_from_detection
from software.classifier.model import DemoClassifier
from software.classifier.train_demo import train_demo_model


def valid_values() -> dict[str, float]:
    return {
        "dominant_frequency_hz": 430.0,
        "second_harmonic_ratio": 0.28,
        "third_harmonic_ratio": 0.11,
        "rms": 0.44,
        "peak_to_peak": 1.7,
        "spectral_energy": 0.95,
        "estimated_snr_db": 22.0,
        "event_duration_seconds": 0.24,
    }


def test_feature_order_is_stable():
    vector = feature_vector_from_detection(valid_values())
    assert FEATURE_NAMES == (
        "dominant_frequency_hz", "second_harmonic_ratio", "third_harmonic_ratio",
        "rms", "peak_to_peak", "spectral_energy", "estimated_snr_db", "event_duration_seconds",
    )
    assert vector.tolist() == [430.0, 0.28, 0.11, 0.44, 1.7, 0.95, 22.0, 0.24]


def test_demo_model_training_and_metadata(tmp_path):
    metadata = train_demo_model(tmp_path, seed=20260915)
    assert metadata["training_data_type"] == "synthetic_demo"
    assert metadata["feature_names"] == list(FEATURE_NAMES)
    assert (tmp_path / "vectorgate_demo_rf.pkl").is_file()
    assert json.loads((tmp_path / "vectorgate_demo_rf.json").read_text())["model_version"] == "vectorgate-demo-rf-v1"


def test_confident_classification_and_low_confidence_unknown(tmp_path):
    train_demo_model(tmp_path)
    classifier = DemoClassifier(tmp_path / "vectorgate_demo_rf.pkl", tmp_path / "vectorgate_demo_rf.json")
    confident = classifier.classify_values(valid_values())
    assert confident.predicted_class.startswith("DEMO_CLASS_")
    assert confident.confidence is not None
    assert confident.is_unknown is False

    ambiguous = valid_values() | {"dominant_frequency_hz": 520.0, "second_harmonic_ratio": 0.29, "third_harmonic_ratio": 0.12, "estimated_snr_db": 16.0}
    rejected = classifier.classify_values(ambiguous)
    assert rejected.predicted_class == "UNKNOWN"
    assert rejected.is_unknown is True


def test_invalid_and_low_quality_values_reject_cleanly(tmp_path):
    train_demo_model(tmp_path)
    classifier = DemoClassifier(tmp_path / "vectorgate_demo_rf.pkl", tmp_path / "vectorgate_demo_rf.json")
    assert classifier.classify_values(valid_values() | {"estimated_snr_db": 2.0}).predicted_class == "UNKNOWN"
    assert classifier.classify_values(valid_values() | {"rms": float("nan")}).predicted_class == "UNKNOWN"
    with pytest.raises(ValueError, match="missing"):
        feature_vector_from_detection({"dominant_frequency_hz": 500.0})


def test_missing_model_is_unknown_not_exception(tmp_path):
    classifier = DemoClassifier(tmp_path / "missing.pkl", tmp_path / "missing.json")
    result = classifier.classify_values(valid_values())
    assert result.predicted_class == "UNKNOWN"
    assert result.confidence is None
    assert classifier.status()["loaded"] is False
