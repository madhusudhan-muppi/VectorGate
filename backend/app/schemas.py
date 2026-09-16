"""Pydantic API contracts and validation rules."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Upper bound on a transient sample batch. At 8 kHz this is ~8 seconds, far
#: more than one flight event, and it keeps a malformed node from posting an
#: unbounded payload.
MAX_SAMPLES = 64_000


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value.astimezone(timezone.utc)


class NodeCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_label: str = Field(min_length=1, max_length=300)
    active: bool = True


class NodeSummary(BaseModel):
    total_detections: int
    latest_detection_at: datetime | None


class NodeResponse(NodeCreate):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    recent_summary: NodeSummary | None = None


class DetectionCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=100)
    recorded_at: datetime
    dominant_frequency_hz: float = Field(ge=0)
    event_duration_seconds: float = Field(gt=0)
    dominant_magnitude: float = Field(ge=0)
    second_harmonic_ratio: float = Field(ge=0)
    third_harmonic_ratio: float = Field(ge=0)
    rms: float = Field(ge=0)
    peak_to_peak: float = Field(ge=0)
    spectral_energy: float = Field(ge=0)
    estimated_snr_db: float
    temperature_c: float | None = None
    humidity_percent: float | None = Field(default=None, ge=0, le=100)
    predicted_class: str | None = Field(default=None, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = Field(default=None, max_length=100)

    # Transient: used to classify on ingest, never persisted. A node sends the
    # waveform so the server extracts features with the same code the model was
    # trained on, rather than the node reimplementing 25 features in firmware.
    samples: list[float] | None = Field(default=None, max_length=MAX_SAMPLES, exclude=True)
    sample_rate_hz: float | None = Field(default=None, gt=0, exclude=True)

    _validate_recorded_at = field_validator("recorded_at")(_aware_utc)

    @model_validator(mode="after")
    def check_sample_batch(self) -> "DetectionCreate":
        if self.samples is not None and self.sample_rate_hz is None:
            raise ValueError("sample_rate_hz is required when samples are supplied")
        if self.samples is not None and not all(math.isfinite(value) for value in self.samples):
            raise ValueError("samples must be finite")
        return self

    @field_validator(
        "dominant_frequency_hz",
        "event_duration_seconds",
        "dominant_magnitude",
        "second_harmonic_ratio",
        "third_harmonic_ratio",
        "rms",
        "peak_to_peak",
        "spectral_energy",
        "estimated_snr_db",
        "temperature_c",
        "humidity_percent",
        "confidence",
        mode="before",
    )
    @classmethod
    def reject_non_finite(cls, value: Any) -> Any:
        if value is not None and isinstance(value, (int, float)):
            import math

            if not math.isfinite(value):
                raise ValueError("numeric values must be finite")
        return value


class DetectionResponse(DetectionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str


class SummaryResponse(BaseModel):
    total_nodes: int
    active_nodes: int
    total_detections: int
    detections_last_hour: int
    detections_last_24h: int
    unknown_detections: int
    latest_detection_at: datetime | None


class MapNodeResponse(BaseModel):
    node_id: str
    name: str
    latitude: float
    longitude: float
    location_label: str
    active: bool
    recent_detection_count: int
    latest_detection_at: datetime | None


class ActivityBucket(BaseModel):
    bucket_start: datetime
    count: int
