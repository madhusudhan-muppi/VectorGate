"""Backend integration tests for serving the WINGBEATS species model.

The trained artifact is a build output, not a repository file, so the tests that
need it skip when it is absent. The contract tests around the transient sample
batch run either way.
"""

from pathlib import Path

import numpy as np
import pytest

from backend.app.services import wingbeats as wingbeats_service
from backend.tests.test_api import detection_payload, node_payload
from software.wingbeats.classifier import DEFAULT_ARTIFACT

ARTIFACT_PRESENT = Path(DEFAULT_ARTIFACT).is_file()
needs_artifact = pytest.mark.skipif(
    not ARTIFACT_PRESENT, reason="run `python3 train_wingbeats.py all` to build the model"
)


def wingbeat_samples(frequency: float, sample_rate: float = 8000.0, duration: float = 0.6) -> list[float]:
    """A tone with harmonics, standing in for an optical wingbeat waveform."""
    t = np.arange(int(sample_rate * duration)) / sample_rate
    wave = np.sin(2 * np.pi * frequency * t)
    wave += 0.3 * np.sin(2 * np.pi * 2 * frequency * t)
    wave += 0.1 * np.sin(2 * np.pi * 3 * frequency * t)
    return [float(value) for value in wave]


def test_sample_batch_requires_a_sample_rate(client):
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    payload = detection_payload()
    payload["samples"] = wingbeat_samples(500.0)
    response = client.post("/api/v1/detections", json=payload)
    assert response.status_code == 422
    assert "sample_rate_hz" in response.text


def test_samples_are_never_persisted_or_returned(client, monkeypatch):
    monkeypatch.setenv("VECTORGATE_WINGBEATS_ENABLED", "1")
    wingbeats_service.reset_wingbeats_classifier()
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    payload = detection_payload()
    payload["samples"] = wingbeat_samples(500.0)
    payload["sample_rate_hz"] = 8000.0
    response = client.post("/api/v1/detections", json=payload)
    assert response.status_code == 201
    assert "samples" not in response.json()
    assert "sample_rate_hz" not in response.json()


def test_wingbeats_disabled_leaves_classification_to_the_demo_path(client, monkeypatch):
    monkeypatch.delenv("VECTORGATE_WINGBEATS_ENABLED", raising=False)
    wingbeats_service.reset_wingbeats_classifier()
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    payload = detection_payload()
    payload["samples"] = wingbeat_samples(500.0)
    payload["sample_rate_hz"] = 8000.0
    response = client.post("/api/v1/detections", json=payload)
    assert response.status_code == 201
    assert response.json()["predicted_class"] is None


@needs_artifact
def test_status_reports_honest_provenance(client, monkeypatch):
    monkeypatch.setenv("VECTORGATE_WINGBEATS_ENABLED", "1")
    wingbeats_service.reset_wingbeats_classifier()
    body = client.get("/api/v1/classifier/wingbeats").json()
    assert body["enabled"] is True
    assert body["loaded"] is True
    assert body["training_data_type"] == "wingbeats_optical"
    assert "session_grouped_accuracy" in body
    assert "Cross-sensor validation" in body["validation_note"]


@needs_artifact
def test_enabled_model_labels_the_detection(client, monkeypatch):
    monkeypatch.setenv("VECTORGATE_WINGBEATS_ENABLED", "1")
    wingbeats_service.reset_wingbeats_classifier()
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    payload = detection_payload(predicted_class="FAKE_CLIENT_LABEL", confidence=1.0)
    payload["samples"] = wingbeat_samples(500.0)
    payload["sample_rate_hz"] = 8000.0
    body = client.post("/api/v1/detections", json=payload).json()
    assert body["model_version"] == "vectorgate-wingbeats-rf-v1"
    # A client-supplied label must never survive ingestion.
    assert body["predicted_class"] != "FAKE_CLIENT_LABEL"


@needs_artifact
def test_high_threshold_rejects_as_unknown(client, monkeypatch):
    monkeypatch.setenv("VECTORGATE_WINGBEATS_ENABLED", "1")
    monkeypatch.setenv("VECTORGATE_WINGBEATS_THRESHOLD", "0.999")
    wingbeats_service.reset_wingbeats_classifier()
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    payload = detection_payload()
    payload["samples"] = wingbeat_samples(500.0)
    payload["sample_rate_hz"] = 8000.0
    body = client.post("/api/v1/detections", json=payload).json()
    assert body["predicted_class"] == "UNKNOWN"


@needs_artifact
def test_resampling_keeps_a_10khz_node_consistent_with_8khz(monkeypatch):
    """A node sampling at 10 kHz must not be classified as a different signal."""
    monkeypatch.delenv("VECTORGATE_WINGBEATS_THRESHOLD", raising=False)
    wingbeats_service.reset_wingbeats_classifier()
    classifier = wingbeats_service.get_wingbeats_classifier()
    at_8k = classifier.classify_samples(np.asarray(wingbeat_samples(500.0, 8000.0)), 8000.0)
    at_10k = classifier.classify_samples(np.asarray(wingbeat_samples(500.0, 10000.0)), 10000.0)
    assert at_8k.predicted_class == at_10k.predicted_class
