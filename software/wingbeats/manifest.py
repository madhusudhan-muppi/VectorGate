"""Build a file manifest over the raw WINGBEATS tree.

Layout in the published dataset::

    <species>/[<age cohort>/]D_YY_MM_DD_HH_MM_SS/F<YYMMDD>_<HHMMSS>_<n>_G_<gain>.wav

The session directory is the only grouping key that works. Each session holds
exactly 100 clips -- a single capture batch from one cage, so clips within a
session may be the same individual recorded repeatedly. A split that lets one
session straddle train and test leaks at the clip level.

Calendar date is *not* usable as a grouping key: 49 of 51 dates in the corpus
carry a single species, and C. quinquefasciatus was recorded on only two days,
so a date-grouped split drops whole classes out of training.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

SESSION_RE = re.compile(r"^D_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})$")

MANIFEST_COLUMNS = ("path", "species", "cohort", "session", "date", "clip")


def _session_date(session: str) -> str | None:
    match = SESSION_RE.match(session)
    if match is None:
        return None
    year, month, day = match.group(1), match.group(2), match.group(3)
    return f"20{year}-{month}-{day}"


def build_manifest(root: str | Path) -> pd.DataFrame:
    """Walk ``root`` and return one row per ``.wav`` file.

    The session is the directory the clip sits in. A cohort is any path segment
    between the species and the session that is not itself a session name --
    the age cohorts present for An. gambiae and C. pipiens only. One session in
    Ae. albopictus is nested inside another; both are treated as distinct
    sessions, which is what the directory structure asserts.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        raise ValueError(f"WINGBEATS root does not exist: {root_path}")

    rows: list[dict[str, object]] = []
    for dirpath, _dirnames, filenames in os.walk(root_path):
        clips = sorted(f for f in filenames if f.lower().endswith(".wav"))
        if not clips:
            continue
        parts = Path(dirpath).relative_to(root_path).parts
        if len(parts) < 2:
            # A species directory holding loose clips has no session identity.
            continue
        species, session = parts[0], parts[-1]
        middle = [p for p in parts[1:-1] if SESSION_RE.match(p) is None]
        cohort = middle[0] if middle else ""
        date = _session_date(session)
        if date is None:
            # Unparseable session name: keep the row but flag the date as
            # unknown rather than guessing one from the filenames.
            date = "unknown"
        session_id = "/".join(parts[1:])
        for clip in clips:
            rows.append(
                {
                    "path": str(Path(dirpath).relative_to(root_path) / clip),
                    "species": species,
                    "cohort": cohort,
                    "session": session_id,
                    "date": date,
                    "clip": clip,
                }
            )

    if not rows:
        raise ValueError(f"no .wav files found under {root_path}")

    frame = pd.DataFrame(rows, columns=list(MANIFEST_COLUMNS))
    return frame.sort_values(["species", "session", "clip"], ignore_index=True)


def read_manifest(path: str | Path) -> pd.DataFrame:
    """Read a manifest or selection CSV without inventing missing values.

    Species with no age cohort carry an empty ``cohort`` string. Left to its
    defaults pandas turns that into NaN, and ``groupby`` then drops those rows
    entirely -- which silently removes four of the six species from sampling.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[])


def summarise(manifest: pd.DataFrame) -> pd.DataFrame:
    """Per-species counts of clips, sessions and distinct dates."""
    grouped = manifest.groupby("species")
    return pd.DataFrame(
        {
            "clips": grouped.size(),
            "sessions": grouped["session"].nunique(),
            "dates": grouped["date"].nunique(),
            "cohorts": grouped["cohort"].nunique(),
        }
    ).sort_values("clips", ascending=False)
