"""Publish Stage 2 synthetic detections to a running local VectorGate API."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np

from backend.app.services.bridge import detection_payload_from_event
from software.data.models import SensorRecording
from software.dsp.pipeline import analyze_sensor_recording
from software.simulator.continuous import SyntheticEvent, generate_continuous_recording


def request_json(base_url: str, method: str, path: str, payload: dict | None = None) -> tuple[int, dict | list]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"could not reach backend: {error.reason}") from error


def run_publisher(base_url: str, node_id: str) -> list[dict]:
    node = {
        "node_id": node_id,
        "name": "Buildathon Demo Gate",
        "latitude": 0.0,
        "longitude": 0.0,
        "location_label": "synthetic integration fixture; not a physical location",
        "active": True,
    }
    try:
        status, _ = request_json(base_url, "POST", "/api/v1/nodes", node)
        print(f"Node registration: {status} Created")
    except RuntimeError as error:
        if "409" not in str(error):
            raise
        print("Node registration: already exists")

    recording = generate_continuous_recording(
        sample_rate_hz=10_000.0,
        duration_seconds=5.0,
        background_noise_level=0.025,
        rng=np.random.default_rng(20260915),
        node_id=node_id,
        temperature_c=24.5,
        humidity_percent=68.0,
        events=[
            SyntheticEvent(1.5, 0.25, 500.0, amplitude=0.8, harmonic_amplitudes={2: 0.3, 3: 0.12}),
            SyntheticEvent(3.0, 0.20, 350.0, amplitude=0.75, harmonic_amplitudes={2: 0.25, 3: 0.10}),
        ],
    )
    # This is an explicit synthetic acquisition time for the integration fixture.
    recording = SensorRecording(
        samples=recording.samples,
        sample_rate_hz=recording.sample_rate_hz,
        source=recording.source,
        start_time=datetime.now(timezone.utc),
        node_id=recording.node_id,
        temperature_c=recording.temperature_c,
        humidity_percent=recording.humidity_percent,
    )
    events = analyze_sensor_recording(recording)
    print("VectorGate Demo Publisher")
    print("-------------------------")
    print(f"Node: {node_id}")
    print("Generated recording...")
    print(f"Events detected: {len(events)}")

    published: list[dict] = []
    for index, event in enumerate(events, start=1):
        payload = detection_payload_from_event(event, recording=recording).model_dump(mode="json")
        print(f"\nPublishing event {index}...")
        status, response = request_json(base_url, "POST", "/api/v1/detections", payload)
        print(f"{status} Created")
        print(f"Detection ID: {response['id']}")
        published.append(response)
    return published


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--node-id", default="VG-DEMO-01")
    args = parser.parse_args()
    run_publisher(args.base_url, args.node_id)


if __name__ == "__main__":
    main()
