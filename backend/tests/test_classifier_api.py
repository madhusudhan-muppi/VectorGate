"""Backend classification integration tests."""

from datetime import datetime, timezone

from backend.app.services import classifier as classifier_service
from backend.tests.test_api import detection_payload, node_payload


def test_classifier_status_endpoint_is_truthful_when_disabled(client):
    response = client.get("/api/v1/classifier/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["training_data_type"] == "synthetic_demo"
    assert body["model_version"] == "vectorgate-demo-rf-v1"
    assert "synthetic_validation_metrics" in body


def test_classifier_persists_model_result_when_enabled(client, monkeypatch):
    monkeypatch.setenv("VECTORGATE_CLASSIFIER_ENABLED", "1")
    classifier_service._classifier = None
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    response = client.post("/api/v1/detections", json=detection_payload(predicted_class="FAKE_CLIENT_LABEL", confidence=1.0))
    assert response.status_code == 201
    body = response.json()
    assert body["predicted_class"].startswith("DEMO_CLASS_") or body["predicted_class"] == "UNKNOWN"
    assert body["model_version"] == "vectorgate-demo-rf-v1"
    assert body["predicted_class"] != "FAKE_CLIENT_LABEL"


def test_existing_null_classification_compatibility_when_disabled(client):
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 201
    response = client.post("/api/v1/detections", json=detection_payload())
    assert response.status_code == 201
    assert response.json()["predicted_class"] is None
    assert response.json()["confidence"] is None
