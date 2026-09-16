"""Publish one mosquito species per region, using real WINGBEATS recordings.

Every detection here is a genuine optical wingbeat recording of a known species
replayed through the full pipeline: the same DSP, the same feature extractor and
the same model that serve live hardware. The species label on screen is whatever
the classifier decides, not the label the file came with. At roughly 69%
session-grouped accuracy some clips will be labelled wrongly or rejected as
Unknown, and that is the honest behaviour to show rather than hide.

The region assignment is presentational. These are DEMO nodes around Chennai,
and placing An. gambiae or C. pipiens on one of them says nothing about where
those species actually occur -- An. gambiae is an Afrotropical vector and is not
established in India. The dashboard labels the whole set as DEMO telemetry.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from backend.app.services.bridge import detection_payload_from_event
from backend.scripts.publisher import request_json
from software.data.models import SensorRecording
from software.dsp.pipeline import analyze_whole_recording

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "Wingbeats"
DEFAULT_MANIFEST = REPO / "data" / "wingbeats_manifest.csv"

#: One species per region, so each map node tells a different story.
SPECIES_REGIONS = [
    ("Ae. aegypti", "DEMO-ADYAR"),
    ("Ae. albopictus", "DEMO-CHROMEPET"),
    ("An. gambiae", "DEMO-GUINDY"),
    ("An. arabiensis", "DEMO-IITM"),
    ("C. pipiens", "DEMO-MARINA"),
    ("C. quinquefasciatus", "DEMO-TAMBARAM"),
]


def load_clip(path: Path) -> tuple[np.ndarray, float]:
    rate, raw = wavfile.read(path)
    samples = np.asarray(raw, dtype=float)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples - samples.mean(), float(rate)


def pick_clips(manifest_path: Path, root: Path, per_species: int, seed: int) -> dict[str, list[Path]]:
    """Choose clips per species, spread across recording sessions.

    Drawing from different sessions rather than one keeps the demo from showing
    a single cage recorded on a single afternoon.
    """
    from software.wingbeats.manifest import read_manifest

    manifest = read_manifest(manifest_path)
    rng = random.Random(seed)
    chosen: dict[str, list[Path]] = {}
    for species, _ in SPECIES_REGIONS:
        rows = manifest[manifest["species"] == species]
        if rows.empty:
            print(f"  no clips found for {species}")
            continue
        sessions = sorted(rows["session"].unique())
        rng.shuffle(sessions)
        picks: list[Path] = []
        for session in sessions[:per_species]:
            candidates = rows[rows["session"] == session]["path"].tolist()
            picks.append(root / rng.choice(candidates))
        chosen[species] = picks
    return chosen


def publish_clip(base_url: str, node_id: str, path: Path) -> dict | None:
    samples, rate = load_clip(path)
    recording = SensorRecording(
        samples=samples,
        sample_rate_hz=rate,
        source="wingbeats-library-clip",
        start_time=datetime.now(timezone.utc),
        node_id=node_id,
    )
    # A library clip is wingbeat from end to end, so there is no quiet
    # background for the transient detector to work against.
    event = analyze_whole_recording(recording)
    payload = detection_payload_from_event(event, recording=recording).model_dump(mode="json")
    payload["samples"] = [float(value) for value in event.samples]
    payload["sample_rate_hz"] = rate
    _, response = request_json(base_url, "POST", "/api/v1/detections", payload)
    return response


def run(base_url: str, root: Path, manifest: Path, per_species: int, seed: int, interval: float) -> None:
    if not root.is_dir():
        raise SystemExit(f"WINGBEATS corpus not found at {root}")
    if not manifest.is_file():
        raise SystemExit(f"manifest not found at {manifest}; run: python3 train_wingbeats.py manifest")

    status, nodes = request_json(base_url, "GET", "/api/v1/nodes")
    if status != 200 or not isinstance(nodes, list):
        raise SystemExit("backend did not return a node list")
    known = {row["node_id"] for row in nodes}
    missing = [node for _, node in SPECIES_REGIONS if node not in known]
    if missing:
        raise SystemExit(
            f"missing demo nodes {missing}; run: python -m backend.scripts.seed_demo"
        )

    print("VectorGate Species Demo")
    print("-----------------------")
    print("Real WINGBEATS recordings replayed through the live pipeline.")
    print("Species labels are the model's own output, not the file labels.")
    print("Region assignment is presentational only.\n")

    clips = pick_clips(manifest, root, per_species, seed)
    agree = total = 0
    for species, node_id in SPECIES_REGIONS:
        paths = clips.get(species, [])
        if not paths:
            continue
        print(f"{species}  ->  {node_id}")
        for path in paths:
            try:
                response = publish_clip(base_url, node_id, path)
            except Exception as error:
                print(f"    {path.name}: failed ({error})")
                continue
            if not response:
                continue
            total += 1
            label = response.get("predicted_class") or "unclassified"
            confidence = response.get("confidence")
            mark = "ok " if label == species else "-- "
            if label == species:
                agree += 1
            suffix = f" ({confidence * 100:.0f}%)" if confidence is not None else ""
            print(
                f"    {mark}{response['dominant_frequency_hz']:6.1f} Hz  "
                f"-> {label}{suffix}"
            )
            if interval:
                time.sleep(interval)
        print()

    if total:
        print(f"model agreed with the dataset label on {agree}/{total} clips ({agree / total:.0%}).")
        print("Expect roughly 69%: that is the session-grouped accuracy this model was measured at.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--per-species", type=int, default=4)
    parser.add_argument("--interval", type=float, default=0.0, help="seconds between publishes")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.per_species < 1:
        raise SystemExit("--per-species must be at least 1")
    try:
        run(args.base_url, args.root, args.manifest, args.per_species, args.seed, args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
