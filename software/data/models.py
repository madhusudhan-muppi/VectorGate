"""Source-neutral data models for sensor recordings and detected events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SensorRecording:
    """A finite sensor sample sequence plus optional acquisition metadata."""

    samples: np.ndarray
    sample_rate_hz: float
    source: str
    start_time: datetime | None = None
    node_id: str | None = None
    temperature_c: float | None = None
    humidity_percent: float | None = None

    def __post_init__(self) -> None:
        samples = np.asarray(self.samples, dtype=float)
        if samples.ndim != 1 or samples.size == 0:
            raise ValueError("samples must be a non-empty one-dimensional array")
        if not np.all(np.isfinite(samples)):
            raise ValueError("samples must contain only finite numeric values")
        if self.sample_rate_hz <= 0 or not np.isfinite(self.sample_rate_hz):
            raise ValueError("sample_rate_hz must be a finite positive value")
        if not self.source or not self.source.strip():
            raise ValueError("source must be a non-empty string")
        for name, value in (
            ("temperature_c", self.temperature_c),
            ("humidity_percent", self.humidity_percent),
        ):
            if value is not None and not np.isfinite(value):
                raise ValueError(f"{name} must be finite when supplied")
        if self.humidity_percent is not None and not 0 <= self.humidity_percent <= 100:
            raise ValueError("humidity_percent must be between 0 and 100")
        object.__setattr__(self, "samples", samples.copy())

    @property
    def duration_seconds(self) -> float:
        return self.samples.size / self.sample_rate_hz


@dataclass(frozen=True)
class EventCandidate:
    """A detected event using an inclusive start and exclusive end index."""

    start_sample: int
    end_sample: int
    sample_rate_hz: float
    samples: np.ndarray

    def __post_init__(self) -> None:
        if self.start_sample < 0 or self.end_sample <= self.start_sample:
            raise ValueError("event indices must satisfy 0 <= start_sample < end_sample")
        if self.end_sample - self.start_sample != len(self.samples):
            raise ValueError("event sample count must match the exclusive index range")
        if self.end_sample > 0 and self.sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        values = np.asarray(self.samples, dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError("event samples must be finite")
        object.__setattr__(self, "samples", values.copy())

    @property
    def start_time_seconds(self) -> float:
        return self.start_sample / self.sample_rate_hz

    @property
    def end_time_seconds(self) -> float:
        return self.end_sample / self.sample_rate_hz

    @property
    def duration_seconds(self) -> float:
        return (self.end_sample - self.start_sample) / self.sample_rate_hz


@dataclass(frozen=True)
class FlightEventResult:
    """Stage 1 features paired with event timing and optional sensor context."""

    start_sample: int
    end_sample: int
    start_time_seconds: float
    end_time_seconds: float
    duration_seconds: float
    samples: np.ndarray
    features: Any
    source: str
    node_id: str | None = None
    temperature_c: float | None = None
    humidity_percent: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a transport-friendly result without inventing missing metadata."""
        result: dict[str, Any] = {
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "start_time_seconds": self.start_time_seconds,
            "end_time_seconds": self.end_time_seconds,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            **self.features.as_dict(),
        }
        for name, value in (
            ("node_id", self.node_id),
            ("temperature_c", self.temperature_c),
            ("humidity_percent", self.humidity_percent),
        ):
            if value is not None:
                result[name] = value
        return result
