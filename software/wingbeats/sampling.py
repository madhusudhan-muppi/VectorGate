"""Session-aware, date-spread subsampling of the WINGBEATS manifest.

Two rules drive this module.

Sample sessions, not files. Drawing clips uniformly at random collapses the
session structure and leaves the splitter with nothing to group on.

Prefer more sessions over more clips per session. For a fixed clip budget,
60 sessions x 50 clips gives the grouped cross-validation far more independent
groups than 30 x 100, and covers more day-to-day variation.

Sessions are allocated round-robin across (cohort, date) strata so that a
species recorded in two separated blocks -- An. arabiensis ran 30 Jan-6 Feb and
again 13-20 Mar -- contributes both, and so that the An. gambiae and C. pipiens
age cohorts are both represented instead of the sample collapsing onto the
larger one.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

DEFAULT_SESSIONS_PER_SPECIES = 60
DEFAULT_CLIPS_PER_SESSION = 50


def _allocate_sessions(
    sessions: pd.DataFrame,
    quota: int,
    rng: np.random.Generator,
) -> list[str]:
    """Pick up to ``quota`` sessions, spread evenly across (cohort, date)."""
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in sessions.itertuples(index=False):
        strata[(row.cohort, row.date)].append(row.session)

    for key in strata:
        order = rng.permutation(len(strata[key]))
        strata[key] = [strata[key][i] for i in order]

    keys = sorted(strata)
    chosen: list[str] = []
    while len(chosen) < quota:
        progressed = False
        for key in keys:
            if not strata[key]:
                continue
            chosen.append(strata[key].pop())
            progressed = True
            if len(chosen) >= quota:
                break
        if not progressed:
            break  # every stratum exhausted
    return chosen


def select(
    manifest: pd.DataFrame,
    sessions_per_species: int = DEFAULT_SESSIONS_PER_SPECIES,
    clips_per_session: int = DEFAULT_CLIPS_PER_SESSION,
    seed: int = 0,
) -> pd.DataFrame:
    """Return the manifest rows making up a balanced, session-aware subset."""
    if sessions_per_species < 2:
        raise ValueError("sessions_per_species must be at least 2 to allow a grouped split")
    if clips_per_session < 1:
        raise ValueError("clips_per_session must be positive")

    rng = np.random.default_rng(seed)
    manifest = manifest.copy()
    manifest["cohort"] = manifest["cohort"].fillna("")
    sessions = (
        manifest.groupby(["species", "cohort", "date", "session"], as_index=False, dropna=False)
        .size()
        .rename(columns={"size": "clips"})
    )

    keep: list[pd.DataFrame] = []
    for species in sorted(sessions["species"].unique()):
        available = sessions[sessions["species"] == species]
        chosen = _allocate_sessions(available, sessions_per_species, rng)
        if len(chosen) < sessions_per_species:
            print(
                f"  note: {species} has only {len(chosen)} sessions "
                f"(asked for {sessions_per_species})"
            )
        for session in chosen:
            clips = manifest[
                (manifest["species"] == species) & (manifest["session"] == session)
            ]
            take = min(clips_per_session, len(clips))
            keep.append(clips.sample(n=take, random_state=int(rng.integers(0, 2**31 - 1))))

    selection = pd.concat(keep, ignore_index=True)
    return selection.sort_values(["species", "session", "clip"], ignore_index=True)


def summarise(selection: pd.DataFrame) -> pd.DataFrame:
    """Per-species counts for the selected subset."""
    grouped = selection.groupby("species")
    return pd.DataFrame(
        {
            "clips": grouped.size(),
            "sessions": grouped["session"].nunique(),
            "dates": grouped["date"].nunique(),
            "cohorts": grouped["cohort"].nunique(),
        }
    ).sort_values("clips", ascending=False)
