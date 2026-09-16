#!/usr/bin/env python3
"""VectorGate -- WINGBEATS species classifier pipeline.

    python3 train_wingbeats.py manifest   # scan Wingbeats/ -> manifest CSV
    python3 train_wingbeats.py sample     # session-aware balanced subset
    python3 train_wingbeats.py extract    # WAVs -> features CSV (slow, once)
    python3 train_wingbeats.py train      # features -> model + honest metrics
    python3 train_wingbeats.py all

Nothing is copied out of ``Wingbeats/``. The subset is a manifest of paths, so
changing the sample costs a rerun of ``sample`` rather than a re-copy, and the
session, date and cohort grouping keys survive -- flattening clips into
per-species folders is what destroyed them last time.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WINGBEATS = ROOT / "Wingbeats"
DATA = ROOT / "data"
MANIFEST = DATA / "wingbeats_manifest.csv"
SELECTION = DATA / "wingbeats_selection.csv"
FEATURES = DATA / "wingbeats_features.csv"
MODEL = DATA / "vectorgate_wingbeats_rf.joblib"


def stage_manifest(args: argparse.Namespace) -> None:
    from software.wingbeats.manifest import build_manifest, summarise

    frame = build_manifest(args.root)
    DATA.mkdir(parents=True, exist_ok=True)
    frame.to_csv(MANIFEST, index=False)
    print(f"wrote {MANIFEST}  ({len(frame)} clips)")
    print(summarise(frame))


def stage_sample(args: argparse.Namespace) -> None:
    from software.wingbeats.manifest import read_manifest
    from software.wingbeats.sampling import select, summarise

    manifest = read_manifest(MANIFEST)
    selection = select(
        manifest,
        sessions_per_species=args.sessions,
        clips_per_session=args.clips,
        seed=args.seed,
    )
    selection.to_csv(SELECTION, index=False)
    print(f"wrote {SELECTION}  ({len(selection)} clips)")
    print(summarise(selection))


def stage_extract(args: argparse.Namespace) -> None:
    from software.wingbeats.extraction import extract_selection
    from software.wingbeats.manifest import read_manifest

    selection = read_manifest(SELECTION)
    print(f"extracting {len(selection)} clips...")
    frame = extract_selection(selection, args.root, processes=args.processes)
    frame.to_csv(FEATURES, index=False)
    print(f"wrote {FEATURES}  shape={frame.shape}")


def stage_train(args: argparse.Namespace) -> None:
    from software.wingbeats.train import train

    train(FEATURES, MODEL, n_splits=args.splits, target_coverage=args.coverage, seed=args.seed)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=["manifest", "sample", "extract", "train", "all"])
    parser.add_argument("--root", default=str(WINGBEATS), help="raw WINGBEATS directory")
    parser.add_argument("--sessions", type=int, default=60, help="sessions sampled per species")
    parser.add_argument("--clips", type=int, default=50, help="clips sampled per session")
    parser.add_argument("--splits", type=int, default=5, help="grouped cross-validation folds")
    parser.add_argument("--coverage", type=float, default=0.90, help="target coverage for the Unknown threshold")
    parser.add_argument("--processes", type=int, default=None, help="extraction worker processes")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    stages = {
        "manifest": stage_manifest,
        "sample": stage_sample,
        "extract": stage_extract,
        "train": stage_train,
    }
    order = ["manifest", "sample", "extract", "train"] if args.stage == "all" else [args.stage]
    for name in order:
        print(f"\n---------------- {name} ----------------")
        stages[name](args)


if __name__ == "__main__":
    main()
