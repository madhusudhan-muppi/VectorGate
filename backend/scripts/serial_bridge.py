"""Stream ESP32 windows into the VectorGate API as classified detections.

The node sends raw ADC windows over serial. This bridge converts them to volts,
runs the existing Stage 2 DSP to find the flight event and its features, and
posts the result with the waveform attached so the server classifies it with the
same feature code the model was trained on.

Nothing here reimplements DSP or feature extraction. The path a real detection
takes is identical to the synthetic one in ``live_demo``, which is the point:
the only thing that changes is where the samples came from.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

import numpy as np

from backend.app.services.bridge import detection_payload_from_event
from backend.scripts.publisher import request_json
from software.data.models import SensorRecording
from software.dsp.pipeline import analyze_sensor_recording, analyze_whole_recording

# VIT Chennai campus, Vandalur-Kelambakkam Road.
DEFAULT_NODE = {
    "node_id": "VG-VITC-01",
    "name": "VIT Chennai",
    "latitude": 12.8406,
    "longitude": 80.1534,
    "location_label": "VIT Chennai campus, Vandalur-Kelambakkam Road",
    "active": True,
}

ADC_FULL_SCALE = 4095.0
ADC_REFERENCE_VOLTS = 3.3

HEADER_RE = re.compile(r"^#EVENT\s+(.*)$")
FIELD_RE = re.compile(r"(\w+)=([^\s]+)")


def parse_fields(text: str) -> dict[str, str]:
    return {key: value for key, value in FIELD_RE.findall(text)}


def ensure_node(base_url: str, node: dict) -> None:
    """Register the sensing node once, so the dashboard can place it."""
    status, existing = request_json(base_url, "GET", "/api/v1/nodes")
    if status == 200 and isinstance(existing, list):
        if any(row.get("node_id") == node["node_id"] for row in existing):
            print(f"node {node['node_id']} already registered")
            return
    request_json(base_url, "POST", "/api/v1/nodes", node)
    print(f"registered node {node['node_id']} at {node['latitude']}, {node['longitude']}")


def counts_to_volts(counts: np.ndarray) -> np.ndarray:
    """ADC counts to mean-centred volts.

    Centring removes the optical DC level, which carries no wingbeat
    information and differs with every alignment of the emitter and detector.
    """
    volts = counts.astype(float) * (ADC_REFERENCE_VOLTS / ADC_FULL_SCALE)
    return volts - volts.mean()


def publish_window(
    base_url: str,
    node_id: str,
    counts: np.ndarray,
    sample_rate_hz: float,
    send_samples: bool = True,
    calibration: bool = False,
) -> dict | None:
    recording = SensorRecording(
        samples=counts_to_volts(counts),
        sample_rate_hz=sample_rate_hz,
        source="esp32-optical-gate",
        start_time=datetime.now(timezone.utc),
        node_id=node_id,
    )
    if calibration:
        # Shared with the library-clip demo, so both take the same DSP path.
        event = analyze_whole_recording(recording)
    else:
        events = analyze_sensor_recording(recording)
        if not events:
            print(
                "  no flight event in this window. The detector wants a burst against a quiet "
                "background; a continuously running chopper is steady state. Use --calibration "
                "to analyse the whole window instead."
            )
            return None
        event = events[0]

    payload = detection_payload_from_event(event, recording=recording).model_dump(mode="json")
    if send_samples:
        payload["samples"] = [float(value) for value in event.samples]
        payload["sample_rate_hz"] = sample_rate_hz
    _, response = request_json(base_url, "POST", "/api/v1/detections", payload)
    return response


def run_bridge(
    port: str, baud: int, base_url: str, node: dict, send_samples: bool, calibration: bool = False
) -> None:
    try:
        import serial
    except ImportError:
        raise SystemExit("pyserial is required: pip install pyserial")

    ensure_node(base_url, node)
    print(f"listening on {port} at {baud} baud; publishing to {base_url}")
    if calibration:
        print("CALIBRATION MODE: whole windows are analysed, transient detection is off.")
        print("This validates the optical and DSP chain, not species identification.")
    print("Ctrl+C to stop.\n")

    with serial.Serial(port, baud, timeout=2) as link:
        collecting = False
        header: dict[str, str] = {}
        values: list[int] = []
        while True:
            raw = link.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            match = HEADER_RE.match(line)
            if match:
                header = parse_fields(match.group(1))
                values = []
                collecting = True
                continue

            if line.startswith("#END"):
                collecting = False
                expected = int(header.get("count", 0) or 0)
                if expected and len(values) != expected:
                    print(f"  dropped a window: expected {expected} samples, received {len(values)}")
                    continue
                # The node reports the rate it actually achieved, not the
                # nominal one; trusting the nominal rate would scale every
                # recovered frequency by the same error.
                rate = float(header.get("rate_hz", 0) or 0)
                if rate <= 0:
                    print("  dropped a window: node did not report a sample rate")
                    continue
                clip_lo = int(header.get("clip_lo", 0) or 0)
                clip_hi = int(header.get("clip_hi", 0) or 0)
                print(
                    f"window seq={header.get('seq', '?')} rate={rate:.1f} Hz "
                    f"mean={header.get('mean', '?')} p2p={header.get('p2p', '?')} "
                    f"clip_lo={clip_lo} clip_hi={clip_hi} reason={header.get('reason', '?')}"
                )
                # Which rail the waveform is stuck against decides the fix, so
                # say it rather than reporting "clipped" and leaving it ambiguous.
                if clip_lo or clip_hi:
                    if clip_lo >= clip_hi:
                        print(
                            f"  clipping at the ADC floor ({clip_lo} samples): the detector output is "
                            "too low. Raise it - more IR (lower the emitter resistor) or a larger "
                            "load resistor - until the clear-beam level sits near 2000 counts."
                        )
                    else:
                        print(
                            f"  clipping at the ADC ceiling ({clip_hi} samples): the detector output is "
                            "too high. Lower the load resistor (10k -> 2.2k -> 1k) or widen the gap "
                            "until the clear-beam level sits near 2000 counts."
                        )
                try:
                    response = publish_window(
                        base_url, node["node_id"], np.asarray(values), rate, send_samples, calibration
                    )
                except Exception as error:
                    print(f"  publish failed: {error}")
                    continue
                if response:
                    label = response.get("predicted_class") or "unclassified"
                    confidence = response.get("confidence")
                    suffix = f" ({confidence * 100:.0f}%)" if confidence is not None else ""
                    print(
                        f"  detection {response['id']}: "
                        f"{response['dominant_frequency_hz']:.1f} Hz -> {label}{suffix}"
                    )
                continue

            if collecting:
                try:
                    values.extend(int(part) for part in line.split(",") if part)
                except ValueError:
                    print(f"  dropped a window: unparseable sample line")
                    collecting = False
                continue

            # Calibration, advice, statistics and warnings from the node.
            if line.startswith("#"):
                print(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM0")
    parser.add_argument("--baud", type=int, default=921600)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--node-id", default=DEFAULT_NODE["node_id"])
    parser.add_argument("--name", default=DEFAULT_NODE["name"])
    parser.add_argument("--latitude", type=float, default=DEFAULT_NODE["latitude"])
    parser.add_argument("--longitude", type=float, default=DEFAULT_NODE["longitude"])
    parser.add_argument("--location-label", default=DEFAULT_NODE["location_label"])
    parser.add_argument(
        "--no-samples",
        action="store_true",
        help="omit the waveform, so the species model cannot classify the detection",
    )
    parser.add_argument(
        "--calibration",
        action="store_true",
        help="analyse each whole window instead of waiting for a transient, for chopper/LED tests",
    )
    args = parser.parse_args()

    node = {
        "node_id": args.node_id,
        "name": args.name,
        "latitude": args.latitude,
        "longitude": args.longitude,
        "location_label": args.location_label,
        "active": True,
    }
    try:
        run_bridge(
            args.port, args.baud, args.base_url, node, not args.no_samples, args.calibration
        )
    except KeyboardInterrupt:
        print("\nbridge stopped.")
        sys.exit(0)
    except RuntimeError as error:
        # Almost always a backend that is not running. A traceback here tells
        # the operator nothing they can act on.
        raise SystemExit(
            f"{error}\n\nIs the API up? Start it with:\n"
            "  VECTORGATE_WINGBEATS_ENABLED=1 VectorGate_venv/bin/python "
            "-m uvicorn backend.app.main:app --reload"
        ) from None


if __name__ == "__main__":
    main()
