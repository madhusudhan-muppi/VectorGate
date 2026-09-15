"""Train the explicitly synthetic VectorGate demonstration classifier."""

from __future__ import annotations

import json
import platform
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from .features import FEATURE_NAMES

MODEL_VERSION = "vectorgate-demo-rf-v1"
ARTIFACT_DIR = Path(__file__).parent / "artifacts"


def generate_demo_dataset(seed: int = 20260915, samples_per_class: int = 180) -> tuple[np.ndarray, np.ndarray]:
    """Create overlapping artificial feature distributions, never biological labels."""
    rng = np.random.default_rng(seed)
    specs = {
        "DEMO_CLASS_A": [430, 0.28, 0.11, 0.44, 1.7, 0.95, 22, 0.24],
        "DEMO_CLASS_B": [540, 0.34, 0.14, 0.49, 1.9, 1.12, 24, 0.29],
        "DEMO_CLASS_C": [670, 0.24, 0.09, 0.40, 1.5, 0.82, 20, 0.20],
    }
    spread = np.array([65, 0.095, 0.055, 0.11, 0.38, 0.32, 7.5, 0.075])
    rows: list[np.ndarray] = []
    labels: list[str] = []
    for label, center in specs.items():
        rows.append(rng.normal(np.asarray(center), spread, size=(samples_per_class, len(FEATURE_NAMES))))
        labels.extend([label] * samples_per_class)
    return np.vstack(rows), np.asarray(labels)


def train_demo_model(output_dir: Path = ARTIFACT_DIR, seed: int = 20260915) -> dict:
    features, labels = generate_demo_dataset(seed)
    train_x, test_x, train_y, test_y = train_test_split(features, labels, test_size=0.25, random_state=seed, stratify=labels)
    model = RandomForestClassifier(n_estimators=160, max_depth=7, random_state=seed, class_weight="balanced")
    model.fit(train_x, train_y)
    predictions = model.predict(test_x)
    probabilities = model.predict_proba(test_x).max(axis=1)
    threshold = 0.62
    rejected = probabilities < threshold
    metadata = {
        "model_version": MODEL_VERSION,
        "model_type": "RandomForestClassifier",
        "feature_names": list(FEATURE_NAMES),
        "training_data_type": "synthetic_demo",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "class_names": list(model.classes_),
        "unknown_threshold": threshold,
        "random_seed": seed,
        "synthetic_training_samples": int(len(train_x)),
        "synthetic_validation_metrics": {
            "label": "SYNTHETIC DEMONSTRATION VALIDATION",
            "accuracy": float(accuracy_score(test_y, predictions)),
            "macro_f1": float(f1_score(test_y, predictions, average="macro")),
            "confusion_matrix": confusion_matrix(test_y, predictions, labels=model.classes_).tolist(),
            "validation_samples": int(len(test_y)),
            "rejected_as_unknown_at_threshold": float(np.mean(rejected)),
        },
        "python_version": platform.python_version(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "vectorgate_demo_rf.pkl").open("wb") as handle:
        pickle.dump(model, handle)
    (output_dir / "vectorgate_demo_rf.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    metadata = train_demo_model()
    metrics = metadata["synthetic_validation_metrics"]
    print("DEMONSTRATION / SYNTHETIC CLASSIFICATION MODEL")
    print("===============================================")
    print(f"Model: {metadata['model_version']}")
    print(f"Synthetic validation accuracy: {metrics['accuracy']:.3f}")
    print(f"Synthetic validation macro F1: {metrics['macro_f1']:.3f}")
    print(f"UNKNOWN threshold: {metadata['unknown_threshold']:.2f}")
    print(f"Validation rejection rate: {metrics['rejected_as_unknown_at_threshold']:.1%}")
    print("WARNING: these are synthetic demonstration metrics, not mosquito species performance.")


if __name__ == "__main__":
    main()
