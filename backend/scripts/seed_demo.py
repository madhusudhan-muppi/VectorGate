"""Seed clearly labelled synthetic nodes and detections for dashboard demos."""

from __future__ import annotations

import argparse
from datetime import timedelta

from sqlalchemy import select

from backend.app.database import SessionLocal, init_db
from backend.app.models import Detection, Node
from backend.app.services.time import utc_now
from backend.app.services.classifier import classify_detection

DEMO_NODES = [
    ("DEMO-MARINA", "DEMO / Marina edge", 13.0500, 80.2824, "DEMO / Marina Beach public landmark"),
    ("DEMO-GUINDY", "DEMO / Guindy greenbelt", 13.0068, 80.2206, "DEMO / Guindy National Park vicinity"),
    ("DEMO-IITM", "DEMO / IIT Madras", 12.9916, 80.2336, "DEMO / IIT Madras campus landmark"),
    ("DEMO-ADYAR", "DEMO / Adyar river", 13.0067, 80.2570, "DEMO / Adyar public river corridor"),
    ("DEMO-CHROMEPET", "DEMO / Chromepet", 12.9516, 80.1462, "DEMO / public transit corridor"),
    ("DEMO-TAMBARAM", "DEMO / Tambaram", 12.9249, 80.1000, "DEMO / public urban landmark"),
]


def _detection(node_id: str, recorded_at, frequency: float, amplitude: float, index: int) -> Detection:
    values = {
        "node_id": node_id,
        "recorded_at": recorded_at,
        "dominant_frequency_hz": frequency,
        "event_duration_seconds": 0.18 + (index % 4) * 0.04,
        "dominant_magnitude": amplitude,
        "second_harmonic_ratio": 0.22 + (index % 3) * 0.04,
        "third_harmonic_ratio": 0.08 + (index % 2) * 0.03,
        "rms": amplitude * 0.55,
        "peak_to_peak": amplitude * 2.1,
        "spectral_energy": amplitude * amplitude * 1.4,
        "estimated_snr_db": 13.0 + (index % 5) * 2.2,
        "temperature_c": 23.5 + (index % 4) * 0.7,
        "humidity_percent": 62.0 + (index % 5) * 2.0,
        "predicted_class": None,
        "confidence": None,
        "model_version": None,
    }
    classification = classify_detection(values)
    if classification is not None:
        values.update(classification)
    return Detection(
        node_id=values["node_id"],
        recorded_at=values["recorded_at"],
        received_at=recorded_at + timedelta(seconds=2),
        **{key: values[key] for key in ("dominant_frequency_hz", "event_duration_seconds", "dominant_magnitude", "second_harmonic_ratio", "third_harmonic_ratio", "rms", "peak_to_peak", "spectral_energy", "estimated_snr_db", "temperature_c", "humidity_percent", "predicted_class", "confidence", "model_version")},
    )


def seed_demo(reset: bool = False) -> int:
    """Create/update DEMO nodes and deterministic recent synthetic activity."""
    init_db()
    db = SessionLocal()
    try:
        if reset:
            demo_ids = [node_id for node_id, *_ in DEMO_NODES]
            for node in db.scalars(select(Node).where(Node.node_id.in_(demo_ids))).all():
                db.delete(node)
            db.commit()

        now = utc_now()
        for node_id, name, latitude, longitude, label in DEMO_NODES:
            node = db.get(Node, node_id)
            if node is None:
                node = Node(
                    node_id=node_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    location_label=label,
                    active=node_id != "DEMO-TAMBARAM",
                    created_at=now,
                )
                db.add(node)
        db.commit()

        # Replace only the seeded activity, preserving non-demo records.
        demo_ids = [node_id for node_id, *_ in DEMO_NODES]
        for detection in db.scalars(select(Detection).where(Detection.node_id.in_(demo_ids))).all():
            db.delete(detection)
        db.commit()

        counts = [14, 10, 7, 3, 2, 0]
        recent_counts = [12, 8, 5, 2, 1, 0]
        frequencies = [500.0, 350.0, 700.0, 517.3, 420.0, 0.0]
        total = 0
        for node_index, ((node_id, *_), count, recent_count) in enumerate(zip(DEMO_NODES, counts, recent_counts, strict=True)):
            for event_index in range(count):
                if event_index < recent_count:
                    hours_ago = 0.25 + event_index * 0.6
                else:
                    hours_ago = 30.0 + ((event_index * 17 + node_index * 11) % 96)
                recorded_at = now - timedelta(hours=hours_ago)
                db.add(_detection(node_id, recorded_at, frequencies[node_index], 0.55 + (event_index % 4) * 0.08, event_index))
                total += 1
        db.commit()
        return total
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="reset DEMO nodes/activity before reseeding")
    args = parser.parse_args()
    total = seed_demo(reset=args.reset)
    print(f"Seeded {len(DEMO_NODES)} clearly labelled DEMO nodes and {total} synthetic detections.")
    print("This data is for dashboard visualization only, not biological surveillance evidence.")


if __name__ == "__main__":
    main()
