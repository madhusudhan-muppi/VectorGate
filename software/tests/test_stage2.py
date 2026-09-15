"""Deterministic tests for Stage 2 recording, detection, and ingestion contracts."""

import numpy as np
import pytest

from software.data.csv import load_csv_recording
from software.data.models import SensorRecording
from software.dsp.events import EventDetectionConfig, detect_events
from software.dsp.pipeline import analyze_sensor_recording
from software.simulator.continuous import SyntheticEvent, generate_continuous_recording


SAMPLE_RATE = 10_000.0


def make_recording(events: list[SyntheticEvent]) -> SensorRecording:
    return generate_continuous_recording(
        sample_rate_hz=SAMPLE_RATE,
        duration_seconds=5.0,
        events=events,
        background_noise_level=0.025,
        rng=np.random.default_rng(42),
    )


def test_background_only_has_no_events():
    assert detect_events(make_recording([])) == []


def test_single_500_hz_event_is_detected_and_analyzed():
    recording = make_recording([SyntheticEvent(1.5, 0.25, 500.0, amplitude=0.8)])
    results = analyze_sensor_recording(recording)
    assert len(results) == 1
    assert abs(results[0].features.dominant_frequency_hz - 500.0) <= 2.0
    assert abs(results[0].start_time_seconds - 1.5) <= 0.1
    assert abs(results[0].end_time_seconds - 1.75) <= 0.1


@pytest.mark.parametrize("frequency", [350.0, 700.0])
def test_detector_does_not_assume_500_hz(frequency: float):
    recording = make_recording([SyntheticEvent(1.5, 0.25, frequency, amplitude=0.8)])
    results = analyze_sensor_recording(recording)
    assert len(results) == 1
    assert abs(results[0].features.dominant_frequency_hz - frequency) <= 2.0


def test_two_separated_events_are_detected():
    recording = make_recording([
        SyntheticEvent(1.5, 0.25, 500.0, amplitude=0.8),
        SyntheticEvent(3.0, 0.20, 350.0, amplitude=0.75),
    ])
    results = analyze_sensor_recording(recording)
    assert len(results) == 2
    assert [round(result.features.dominant_frequency_hz) for result in results] == [500, 350]


def test_short_noise_spike_is_rejected_by_minimum_duration():
    samples = np.random.default_rng(4).normal(0.0, 0.025, size=50_000)
    samples[15_000:15_010] += 4.0
    recording = SensorRecording(samples, SAMPLE_RATE, "spike-test")
    config = EventDetectionConfig(pre_trigger_seconds=0.0, post_trigger_seconds=0.0)
    assert detect_events(recording, config) == []


def test_triggered_frames_with_small_gap_merge():
    recording = make_recording([
        SyntheticEvent(1.0, 0.14, 500.0, amplitude=0.8),
        SyntheticEvent(1.17, 0.14, 500.0, amplitude=0.8),
    ])
    config = EventDetectionConfig(merge_gap_seconds=0.06)
    events = detect_events(recording, config)
    assert len(events) == 1


def test_metadata_survives_event_pipeline():
    recording = generate_continuous_recording(
        sample_rate_hz=SAMPLE_RATE,
        duration_seconds=2.0,
        events=[SyntheticEvent(0.8, 0.25, 500.0, amplitude=0.8)],
        background_noise_level=0.025,
        rng=np.random.default_rng(5),
        node_id="VG-TEST-01",
        temperature_c=23.5,
        humidity_percent=61.0,
    )
    result = analyze_sensor_recording(recording)[0]
    payload = result.as_dict()
    assert payload["node_id"] == "VG-TEST-01"
    assert payload["temperature_c"] == 23.5
    assert payload["humidity_percent"] == 61.0


def test_valid_sample_csv_loads_with_metadata(tmp_path):
    path = tmp_path / "recording.csv"
    path.write_text("sample,value\n0,1.0\n1,2.0\n2,3.0\n", encoding="utf-8")
    recording = load_csv_recording(
        path,
        sample_rate_hz=10_000.0,
        node_id="VG-CSV-01",
        temperature_c=22.0,
        humidity_percent=55.0,
    )
    assert recording.samples.tolist() == [1.0, 2.0, 3.0]
    assert recording.node_id == "VG-CSV-01"
    assert recording.temperature_c == 22.0


@pytest.mark.parametrize("content", ["", "sample,value\n", "wrong,value\n1,2\n"])
def test_empty_or_malformed_csv_is_rejected(tmp_path, content: str):
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_csv_recording(path, sample_rate_hz=10_000.0)