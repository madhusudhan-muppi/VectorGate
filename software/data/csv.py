"""Strict CSV ingestion for recorded sensor waveforms."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .models import SensorRecording


def load_csv_recording(
    path: str | Path,
    sample_rate_hz: float | None = None,
    *,
    node_id: str | None = None,
    temperature_c: float | None = None,
    humidity_percent: float | None = None,
) -> SensorRecording:
    """Load ``sample,value`` or ``time_seconds,value`` CSV data.

    ``sample,value`` requires an external sample rate. For ``time_seconds,value``
    the rate is inferred only when timestamps are finite, strictly increasing,
    and uniformly spaced; an explicitly supplied rate takes precedence after a
    consistency check. No missing or malformed rows are silently discarded.
    """
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ValueError(f"CSV file does not exist: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV file is empty") from exc
        header = [item.strip() for item in header]
        if header not in (["sample", "value"], ["time_seconds", "value"]):
            raise ValueError("CSV header must be exactly sample,value or time_seconds,value")

        rows: list[tuple[float, float]] = []
        for line_number, row in enumerate(reader, start=2):
            if len(row) != 2 or any(not item.strip() for item in row):
                raise ValueError(f"malformed CSV row at line {line_number}")
            try:
                rows.append((float(row[0]), float(row[1])))
            except ValueError as exc:
                raise ValueError(f"non-numeric CSV row at line {line_number}") from exc

    if not rows:
        raise ValueError("CSV file contains no samples")
    positions = np.asarray([row[0] for row in rows], dtype=float)
    values = np.asarray([row[1] for row in rows], dtype=float)
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(values)):
        raise ValueError("CSV values must be finite")

    if header[0] == "sample":
        if sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required for sample,value CSV files")
        if not np.allclose(positions, np.arange(len(positions), dtype=float)):
            raise ValueError("sample column must contain consecutive zero-based sample indices")
    else:
        if len(positions) < 2:
            raise ValueError("time_seconds CSV requires at least two samples")
        deltas = np.diff(positions)
        if np.any(deltas <= 0) or not np.allclose(deltas, deltas[0], rtol=1e-5, atol=1e-9):
            raise ValueError("time_seconds must be strictly increasing and uniformly spaced")
        inferred_rate = 1.0 / float(np.mean(deltas))
        if sample_rate_hz is None:
            sample_rate_hz = inferred_rate
        elif not np.isclose(sample_rate_hz, inferred_rate, rtol=1e-5, atol=1e-3):
            raise ValueError("supplied sample_rate_hz disagrees with time_seconds spacing")

    return SensorRecording(
        samples=values,
        sample_rate_hz=float(sample_rate_hz),
        source=f"csv:{csv_path}",
        node_id=node_id,
        temperature_c=temperature_c,
        humidity_percent=humidity_percent,
    )
