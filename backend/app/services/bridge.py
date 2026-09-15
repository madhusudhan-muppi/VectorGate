"""Bridge Stage 2 FlightEventResult values to API detection payloads."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import ValidationError

from software.data.models import FlightEventResult, SensorRecording

from ..schemas import DetectionCreate


def detection_payload_from_event(
    event: FlightEventResult,
    *,
    recorded_at: datetime | None = None,
    recording: SensorRecording | None = None,
) -> DetectionCreate:
    """Convert existing DSP output without recalculating or classifying it.

    A physical timestamp must be supplied explicitly, or derived from a
    recording's explicit timezone-aware ``start_time``. Synthetic recordings
    without one cannot silently be presented as physical measurement times.
    """
    if recorded_at is None and recording is not None and recording.start_time is not None:
        recorded_at = recording.start_time + timedelta(seconds=event.start_time_seconds)
    if recorded_at is None:
        raise ValueError("recorded_at or a recording with timezone-aware start_time is required")
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("recorded_at must be timezone-aware")
    if not event.node_id:
        raise ValueError("event must contain node_id for API publishing")
    values = event.features.as_dict()
    return DetectionCreate(
        node_id=event.node_id,
        recorded_at=recorded_at.astimezone(timezone.utc),
        event_duration_seconds=event.duration_seconds,
        temperature_c=event.temperature_c,
        humidity_percent=event.humidity_percent,
        **values,
    )
