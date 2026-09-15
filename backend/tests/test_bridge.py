"""Tests for the Stage 2 to API payload bridge."""

from datetime import datetime, timezone

import numpy as np
import pytest

from backend.app.services.bridge import detection_payload_from_event
from software.data.models import FlightEventResult, SensorRecording
from software.dsp.analysis import extract_features


def event(node_id="VG-BRIDGE-01"):
    samples = np.sin(2 * np.pi * 500 * np.arange(5000) / 10000)
    features, _ = extract_features(samples, 10000)
    return FlightEventResult(0, 5000, 0.0, 0.5, 0.5, samples, features, "test", node_id=node_id, temperature_c=23.0, humidity_percent=60.0)


def test_flight_event_result_bridges_without_recalculating():
    payload = detection_payload_from_event(event(), recorded_at=datetime(2026, 9, 15, tzinfo=timezone.utc))
    assert payload.node_id == "VG-BRIDGE-01"
    assert payload.dominant_frequency_hz == 500.0
    assert payload.event_duration_seconds == 0.5
    assert payload.temperature_c == 23.0


def test_bridge_requires_explicit_physical_timestamp_and_node():
    with pytest.raises(ValueError, match="recorded_at"):
        detection_payload_from_event(event())
    with pytest.raises(ValueError, match="node_id"):
        detection_payload_from_event(event(node_id=None), recorded_at=datetime.now(timezone.utc))


def test_bridge_derives_timestamp_only_from_explicit_recording_start():
    recording = SensorRecording(
        np.zeros(6000),
        10000,
        "recorded",
        start_time=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    payload = detection_payload_from_event(event(), recording=recording)
    assert payload.recorded_at.isoformat() == "2026-09-15T12:00:00+00:00"
