"""Continuously publish synthetic Stage 2 detections for presentations."""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import numpy as np

from backend.app.services.bridge import detection_payload_from_event
from backend.scripts.publisher import request_json
from software.data.models import SensorRecording
from software.dsp.pipeline import analyze_sensor_recording
from software.simulator.continuous import SyntheticEvent, generate_continuous_recording

FREQUENCIES = (350.0, 500.0, 517.3, 700.0)


def publish_once(base_url: str, node_id: str, frequency: float, seed: int) -> dict:
    recording = generate_continuous_recording(
        sample_rate_hz=10_000.0,
        duration_seconds=1.2,
        background_noise_level=0.025,
        rng=np.random.default_rng(seed),
        node_id=node_id,
        temperature_c=24.0 + (seed % 4) * 0.5,
        humidity_percent=64.0 + (seed % 5),
        events=[SyntheticEvent(0.45, 0.22, frequency, amplitude=0.75, harmonic_amplitudes={2: 0.27, 3: 0.1})],
    )
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
    if not events:
        raise RuntimeError("synthetic live demo produced no event")
    payload = detection_payload_from_event(events[0], recording=recording).model_dump(mode="json")
    _, response = request_json(base_url, "POST", "/api/v1/detections", payload)
    return response


def run_live_demo(base_url: str, interval_seconds: float) -> None:
    status, nodes = request_json(base_url, "GET", "/api/v1/nodes")
    if status != 200 or not isinstance(nodes, list):
        raise RuntimeError("backend did not return a node list; run seed_demo first")
    demo_nodes = [node["node_id"] for node in nodes if node["node_id"].startswith("DEMO-")]
    if not demo_nodes:
        raise RuntimeError("no DEMO nodes found; run python -m backend.scripts.seed_demo first")

    print("VectorGate Live Demo")
    print("--------------------")
    print("Synthetic presentation telemetry only; no biological claims.")
    print(f"Publishing to {base_url} every {interval_seconds:.1f}s. Press Ctrl+C to stop.")
    index = 0
    try:
        while True:
            node_id = demo_nodes[index % len(demo_nodes)]
            frequency = FREQUENCIES[index % len(FREQUENCIES)]
            response = publish_once(base_url, node_id, frequency, 20260915 + index)
            print(f"Published synthetic detection {response['id']} -> {node_id} at {frequency:.1f} Hz")
            index += 1
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nLive demo stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--interval", type=float, default=8.0)
    args = parser.parse_args()
    if args.interval <= 0:
        raise SystemExit("--interval must be positive")
    run_live_demo(args.base_url, args.interval)


if __name__ == "__main__":
    main()
