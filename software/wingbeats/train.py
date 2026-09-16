"""Train and honestly evaluate the WINGBEATS species classifier.

Three numbers are reported, and only one of them should be quoted.

The random split is optimistic and is printed only to size the leak. Clips from
one capture session land on both sides of it, and a session is 100 recordings
of one cage, so it measures memorisation of sessions.

The session-grouped split is the headline. No session straddles the split, and
because every species has at least 194 sessions, ``StratifiedGroupKFold`` can
keep all six classes in training -- which a date-grouped split cannot do.

The date-grouped split is a robustness bound over the five species with five or
more recording days. C. quinquefasciatus is excluded because it was recorded on
only two. It quantifies the day/colony effect that the session split cannot
remove, since 49 of 51 dates in the corpus carry a single species.

Two feature sets are fitted. The scale-invariant set drops the amplitude
features, which depend on recording gain and on how close the insect flew; it
is the set that has any chance of transferring to VectorGate hardware.

An open-set rejection threshold is calibrated on out-of-fold probabilities so
the deployed model can answer Unknown, matching the behaviour of
:class:`software.classifier.model.DemoClassifier`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from .features import feature_names, scale_invariant_names

METADATA_COLUMNS = ("path", "species", "cohort", "session", "date", "clip")
DEFAULT_SPLITS = 5
DEFAULT_TARGET_COVERAGE = 0.90
MIN_DATES_FOR_DATE_SPLIT = 5


def _forest(seed: int = 0) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        n_jobs=-1,
        class_weight="balanced",
        random_state=seed,
    )


@dataclass
class Evaluation:
    label: str
    accuracy: float
    n_train: int
    n_test: int


def _report(y_true: np.ndarray, y_pred: np.ndarray, label: str, n_train: int) -> Evaluation:
    accuracy = accuracy_score(y_true, y_pred)
    print(f"\n===== {label} =====")
    print(f"accuracy: {accuracy:.4f}   (train n={n_train}, test n={len(y_true)})")
    print(classification_report(y_true, y_pred, digits=3, zero_division=0))
    labels = sorted(np.unique(np.concatenate([y_true, y_pred])))
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    width = max(len(l) for l in labels) + 1
    print("confusion matrix (rows = true):")
    print(" " * width + "".join(f"{l.split()[-1][:7]:>8}" for l in labels))
    for name, row in zip(labels, matrix):
        print(f"{name:<{width}}" + "".join(f"{v:8d}" for v in row))
    return Evaluation(label, accuracy, n_train, len(y_true))


def _out_of_fold(
    X: pd.DataFrame,
    y: np.ndarray,
    groups: np.ndarray,
    n_splits: int,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Out-of-fold predictions and probabilities from a grouped split."""
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    classes = sorted(np.unique(y))
    predictions = np.empty(len(y), dtype=object)
    probabilities = np.zeros((len(y), len(classes)), dtype=float)
    for train_idx, test_idx in splitter.split(X, y, groups):
        model = _forest(seed)
        model.fit(X.iloc[train_idx], y[train_idx])
        probs = model.predict_proba(X.iloc[test_idx])
        for column, cls in enumerate(model.classes_):
            probabilities[test_idx, classes.index(cls)] = probs[:, column]
        predictions[test_idx] = model.predict(X.iloc[test_idx])
    return predictions.astype(str), probabilities, classes


def _rejection_table(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
    target_coverage: float,
) -> float:
    """Print the coverage/accuracy trade-off and return the chosen threshold."""
    confidence = probabilities.max(axis=1)
    predicted = np.asarray(classes)[probabilities.argmax(axis=1)]
    correct = predicted == y_true

    print("\n===== OPEN-SET REJECTION (calibrated out-of-fold) =====")
    print(f"{'threshold':>10} {'coverage':>10} {'accuracy on accepted':>22}")
    for threshold in np.arange(0.30, 0.91, 0.05):
        accepted = confidence >= threshold
        coverage = accepted.mean()
        accuracy = correct[accepted].mean() if accepted.any() else float("nan")
        print(f"{threshold:10.2f} {coverage:10.3f} {accuracy:22.3f}")

    chosen = float(np.quantile(confidence, 1.0 - target_coverage))
    accepted = confidence >= chosen
    print(
        f"\nchosen threshold {chosen:.3f} for target coverage {target_coverage:.0%}: "
        f"coverage {accepted.mean():.3f}, accuracy on accepted "
        f"{correct[accepted].mean():.3f}"
    )
    print("Clips below the threshold are reported as Unknown, not as a species.")
    return chosen


def train(
    features_path: str | Path,
    model_path: str | Path,
    n_splits: int = DEFAULT_SPLITS,
    target_coverage: float = DEFAULT_TARGET_COVERAGE,
    seed: int = 0,
) -> None:
    import joblib

    frame = pd.read_csv(features_path)
    all_features = [c for c in feature_names() if c in frame.columns]
    invariant = [c for c in scale_invariant_names() if c in frame.columns]
    y = frame["species"].to_numpy(dtype=str)
    groups = frame["session"].to_numpy(dtype=str)
    dates = frame["date"].to_numpy(dtype=str)

    print(f"clips: {len(frame)}   features: {len(all_features)}")
    print(f"sessions: {pd.Series(groups).nunique()}   dates: {pd.Series(dates).nunique()}")
    print("\nclips per species:")
    print(frame.groupby("species").agg(clips=("path", "size"), sessions=("session", "nunique")))

    missing = frame[all_features].isna().sum()
    if missing.any():
        print("\nfeatures marked missing (harmonic above Nyquist):")
        for name, count in missing[missing > 0].items():
            print(f"  {name:<20} {count:6d}  ({count / len(frame):.1%})")

    results: dict[str, Evaluation] = {}
    bundle_threshold = 0.0
    bundle_model = None
    bundle_columns: list[str] = []

    for set_name, columns in (("all features", all_features), ("scale-invariant", invariant)):
        print(f"\n\n################ FEATURE SET: {set_name} ({len(columns)} features) ################")
        X = frame[columns]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, stratify=y, random_state=seed
        )
        optimistic = _forest(seed)
        optimistic.fit(X_train, y_train)
        random_eval = _report(
            y_test, optimistic.predict(X_test), "RANDOM SPLIT (optimistic, leaks sessions)", len(y_train)
        )

        predictions, probabilities, classes = _out_of_fold(X, y, groups, n_splits, seed)
        grouped_eval = _report(
            y,
            predictions,
            f"SESSION-GROUPED {n_splits}-FOLD (quote this one)",
            len(y) - len(y) // n_splits,
        )
        print(f"\nleak gap (random - session-grouped): {random_eval.accuracy - grouped_eval.accuracy:+.4f}")
        results[set_name] = grouped_eval

        threshold = _rejection_table(y, probabilities, classes, target_coverage)

        date_counts = pd.DataFrame({"species": y, "date": dates}).groupby("species")["date"].nunique()
        eligible = date_counts[date_counts >= MIN_DATES_FOR_DATE_SPLIT].index.tolist()
        mask = np.isin(y, eligible)
        if len(eligible) >= 2 and mask.sum() > 0:
            n_date_splits = min(n_splits, int(date_counts[eligible].min()))
            print(
                f"\n(date-grouped robustness check over {len(eligible)} species with "
                f">={MIN_DATES_FOR_DATE_SPLIT} recording days; "
                f"excluded: {sorted(set(np.unique(y)) - set(eligible))})"
            )
            subset_X = X[mask].reset_index(drop=True)
            n_subset_train = int(mask.sum() - mask.sum() // n_date_splits)
            # Same species, same folds count, grouped by session instead of by
            # date -- so the two numbers below differ only in the grouping key.
            session_subset, _, _ = _out_of_fold(
                subset_X, y[mask], groups[mask], n_date_splits, seed
            )
            session_subset_eval = _report(
                y[mask],
                session_subset,
                f"SESSION-GROUPED {n_date_splits}-FOLD ({len(eligible)} species, comparison baseline)",
                n_subset_train,
            )
            date_predictions, _, _ = _out_of_fold(
                subset_X, y[mask], dates[mask], n_date_splits, seed
            )
            date_eval = _report(
                y[mask],
                date_predictions,
                f"DATE-GROUPED {n_date_splits}-FOLD ({len(eligible)} species, robustness bound)",
                n_subset_train,
            )
            print(
                f"\nday effect on the same {len(eligible)} species: "
                f"{session_subset_eval.accuracy:.4f} session-grouped -> "
                f"{date_eval.accuracy:.4f} date-grouped "
                f"({date_eval.accuracy - session_subset_eval.accuracy:+.4f})"
            )

        final = _forest(seed)
        final.fit(X, y)
        importances = sorted(zip(columns, final.feature_importances_), key=lambda t: -t[1])
        print(f"\ntop features ({set_name}):")
        for name, value in importances[:15]:
            print(f"  {name:<22} {value:.4f}")

        if set_name == "scale-invariant":
            bundle_model, bundle_columns, bundle_threshold = final, columns, threshold

    print("\n\n================ SUMMARY (session-grouped) ================")
    for set_name, evaluation in results.items():
        print(f"  {set_name:<18} {evaluation.accuracy:.4f}")
    print(
        "\nThe scale-invariant model is saved, because the amplitude features do not\n"
        "transfer to different optics, gain or flight distance. Cross-sensor validation\n"
        "on VectorGate hardware remains outstanding."
    )

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": bundle_model,
            "columns": bundle_columns,
            "classes": list(bundle_model.classes_),
            "unknown_threshold": bundle_threshold,
            "model_version": "vectorgate-wingbeats-rf-v1",
            "training_sample_rate_hz": 8000.0,
            "feature_set": "scale-invariant",
            "dataset": "WINGBEATS (Potamitis & Rigakis, IEEE Sensors J. 16(15):6053-6061, 2016)",
            "split": f"StratifiedGroupKFold(n_splits={n_splits}) on recording session",
            "session_grouped_accuracy": results["scale-invariant"].accuracy,
        },
        model_path,
    )
    print(f"\nsaved {model_path}")
