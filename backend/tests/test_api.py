"""API contract and persistence tests."""

from datetime import datetime, timedelta, timezone


def node_payload(node_id="VG-TEST-01"):
    return {
        "node_id": node_id,
        "name": "Test Gate",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "location_label": "Test location",
        "active": True,
    }


def detection_payload(node_id="VG-TEST-01", **overrides):
    payload = {
        "node_id": node_id,
        "recorded_at": "2026-09-15T12:00:00Z",
        "dominant_frequency_hz": 500.0,
        "event_duration_seconds": 0.25,
        "dominant_magnitude": 0.8,
        "second_harmonic_ratio": 0.3,
        "third_harmonic_ratio": 0.12,
        "rms": 0.6,
        "peak_to_peak": 1.7,
        "spectral_energy": 1.2,
        "estimated_snr_db": 22.0,
        "temperature_c": 24.5,
        "humidity_percent": 65.0,
    }
    payload.update(overrides)
    return payload


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_create_list_get_node_and_duplicate_behavior(client):
    created = client.post("/api/v1/nodes", json=node_payload())
    assert created.status_code == 201
    assert created.json()["node_id"] == "VG-TEST-01"
    assert created.json()["recent_summary"]["total_detections"] == 0
    assert client.post("/api/v1/nodes", json=node_payload()).status_code == 409
    assert len(client.get("/api/v1/nodes").json()) == 1
    fetched = client.get("/api/v1/nodes/VG-TEST-01")
    assert fetched.status_code == 200
    assert fetched.json()["location_label"] == "Test location"
    assert client.get("/api/v1/nodes/missing").status_code == 404


def test_invalid_coordinates_are_rejected(client):
    response = client.post("/api/v1/nodes", json={**node_payload(), "latitude": 91})
    assert response.status_code == 422


def test_create_validate_list_filter_and_get_detection(client):
    client.post("/api/v1/nodes", json=node_payload())
    created = client.post("/api/v1/detections", json=detection_payload())
    assert created.status_code == 201
    assert created.json()["predicted_class"] is None
    detection_id = created.json()["id"]
    assert client.post("/api/v1/detections", json=detection_payload("missing")).status_code == 404
    assert client.post("/api/v1/detections", json=detection_payload(rms=-1)).status_code == 422
    assert client.get(f"/api/v1/detections/{detection_id}").json()["id"] == detection_id
    assert len(client.get("/api/v1/detections", params={"node_id": "VG-TEST-01", "limit": 10}).json()) == 1
    assert client.get("/api/v1/detections", params={"predicted_class": "mosquito"}).json() == []
    assert client.get("/api/v1/detections/999").status_code == 404


def test_empty_summary_and_map_are_valid(client):
    summary = client.get("/api/v1/stats/summary").json()
    assert summary == {
        "total_nodes": 0,
        "active_nodes": 0,
        "total_detections": 0,
        "detections_last_hour": 0,
        "detections_last_24h": 0,
        "unknown_detections": 0,
        "latest_detection_at": None,
    }
    assert client.get("/api/v1/map/nodes").json() == []


def test_summary_map_activity_and_node_summary(client):
    client.post("/api/v1/nodes", json=node_payload())
    client.post("/api/v1/nodes", json={**node_payload("VG-TEST-02"), "active": False})
    client.post("/api/v1/detections", json=detection_payload())
    client.post("/api/v1/detections", json=detection_payload(recorded_at="2026-09-15T12:30:00Z", predicted_class="unknown"))
    summary = client.get("/api/v1/stats/summary").json()
    assert summary["total_nodes"] == 2
    assert summary["active_nodes"] == 1
    assert summary["total_detections"] == 2
    assert summary["unknown_detections"] == 1
    node = client.get("/api/v1/nodes/VG-TEST-01").json()
    assert node["recent_summary"]["total_detections"] == 2
    map_data = client.get("/api/v1/map/nodes").json()
    assert map_data[0]["recent_detection_count"] == 2
    assert map_data[0]["latitude"] == 12.9716
    activity = client.get(
        "/api/v1/nodes/VG-TEST-01/activity",
        params={"since": "2026-09-15T11:00:00Z", "until": "2026-09-15T14:00:00Z", "bucket_seconds": 3600},
    )
    assert activity.status_code == 200
    assert sum(bucket["count"] for bucket in activity.json()) == 2


def test_cors_allows_configured_local_frontend(client):
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
