"""Parallel feature extraction driver over a selected manifest."""

from __future__ import annotations

from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from .features import extract

METADATA_COLUMNS = ("path", "species", "cohort", "session", "date", "clip")


def _one(job: tuple[str, str, str, str, str, str]) -> dict[str, object] | None:
    path, species, cohort, session, date, clip = job
    row = extract(path)
    if row is None:
        return None
    row["path"] = path
    row["species"] = species
    row["cohort"] = cohort
    row["session"] = session
    row["date"] = date
    row["clip"] = clip
    return row


def extract_selection(
    selection: pd.DataFrame,
    root: str | Path,
    processes: int | None = None,
) -> pd.DataFrame:
    """Extract features for every row of ``selection``.

    Rows that cannot be read or are too short to analyse are dropped and
    counted; they are never silently replaced with zeros.
    """
    root_path = Path(root)
    jobs = [
        (
            str(root_path / row.path),
            row.species,
            row.cohort,
            row.session,
            row.date,
            row.clip,
        )
        for row in selection.itertuples(index=False)
    ]
    workers = processes or max(1, cpu_count() - 1)

    rows: list[dict[str, object]] = []
    with Pool(workers) as pool:
        for index, result in enumerate(pool.imap_unordered(_one, jobs, chunksize=64), start=1):
            if result is not None:
                rows.append(result)
            if index % 2000 == 0:
                print(f"  {index}/{len(jobs)}", flush=True)

    dropped = len(jobs) - len(rows)
    if dropped:
        print(f"  dropped {dropped} unreadable or too-short clips")
    if not rows:
        raise ValueError("feature extraction produced no rows")

    frame = pd.DataFrame(rows)
    ordered = [c for c in METADATA_COLUMNS if c in frame.columns]
    feature_cols = [c for c in frame.columns if c not in ordered]
    return frame[ordered + sorted(feature_cols)]
