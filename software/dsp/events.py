"""Explainable frame-energy event detection for continuous recordings."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from software.data.models import EventCandidate, SensorRecording


@dataclass(frozen=True)
class EventDetectionConfig:
    """Parameters for robust RMS thresholding and event segmentation."""

    frame_length_seconds: float = 0.05
    hop_seconds: float = 0.01
    trigger_sigma: float = 6.0
    min_event_duration_seconds: float = 0.08
    max_event_duration_seconds: float = 0.60
    merge_gap_seconds: float = 0.04
    pre_trigger_seconds: float = 0.03
    post_trigger_seconds: float = 0.03

    def __post_init__(self) -> None:
        if self.frame_length_seconds <= 0 or self.hop_seconds <= 0:
            raise ValueError("frame_length_seconds and hop_seconds must be positive")
        if self.trigger_sigma <= 0 or self.min_event_duration_seconds <= 0:
            raise ValueError("trigger_sigma and min_event_duration_seconds must be positive")
        if self.max_event_duration_seconds < self.min_event_duration_seconds:
            raise ValueError("maximum duration must not be below minimum duration")
        if self.merge_gap_seconds < 0 or self.pre_trigger_seconds < 0 or self.post_trigger_seconds < 0:
            raise ValueError("gap and padding values must be non-negative")


def _frame_rms(samples: np.ndarray, frame_length: int, hop: int) -> tuple[np.ndarray, np.ndarray]:
    starts = np.arange(0, max(0, len(samples) - frame_length + 1), hop, dtype=int)
    if not len(starts):
        return np.array([], dtype=float), starts
    values = np.empty(len(starts), dtype=float)
    for index, start in enumerate(starts):
        frame = samples[start : start + frame_length]
        centered = frame - np.mean(frame)
        values[index] = np.sqrt(np.mean(np.square(centered)))
    return values, starts


def detect_events(
    recording: SensorRecording,
    config: EventDetectionConfig | None = None,
) -> list[EventCandidate]:
    """Detect temporary energy rises and return padded sample windows.

    The baseline is the median frame RMS. Its robust spread is the MAD scaled
    to Gaussian sigma, with a small baseline-relative floor for stable behavior
    on nearly constant recordings. This is intentionally explainable and does
    not identify insects; background transients can still produce candidates.
    """
    settings = config or EventDetectionConfig()
    frame_length = max(2, int(round(settings.frame_length_seconds * recording.sample_rate_hz)))
    hop = max(1, int(round(settings.hop_seconds * recording.sample_rate_hz)))
    rms_values, starts = _frame_rms(recording.samples, frame_length, hop)
    if not len(rms_values):
        return []

    baseline = float(np.median(rms_values))
    mad = float(np.median(np.abs(rms_values - baseline)))
    spread = max(1.4826 * mad, baseline * 0.05, np.finfo(float).eps)
    threshold = baseline + settings.trigger_sigma * spread
    triggered = rms_values > threshold
    if not np.any(triggered):
        return []

    triggered_indices = np.flatnonzero(triggered)
    groups: list[tuple[int, int]] = []
    group_start = int(triggered_indices[0])
    group_end = group_start
    for index in triggered_indices[1:]:
        gap_seconds = (starts[index] - starts[group_end]) / recording.sample_rate_hz
        if gap_seconds <= settings.merge_gap_seconds:
            group_end = int(index)
        else:
            groups.append((group_start, group_end))
            group_start = int(index)
            group_end = group_start
    groups.append((group_start, group_end))

    candidates: list[EventCandidate] = []
    pre_padding = int(round(settings.pre_trigger_seconds * recording.sample_rate_hz))
    post_padding = int(round(settings.post_trigger_seconds * recording.sample_rate_hz))
    max_samples = int(round(settings.max_event_duration_seconds * recording.sample_rate_hz))
    min_samples = int(round(settings.min_event_duration_seconds * recording.sample_rate_hz))
    for first_frame, last_frame in groups:
        triggered_span = int(starts[last_frame] - starts[first_frame])
        if triggered_span < min_samples:
            continue
        start = max(0, int(starts[first_frame]) - pre_padding)
        end = min(len(recording.samples), int(starts[last_frame]) + frame_length + post_padding)
        if end - start < min_samples:
            continue
        if end - start > max_samples:
            center = (start + end) // 2
            start = max(0, center - max_samples // 2)
            end = min(len(recording.samples), start + max_samples)
        candidates.append(
            EventCandidate(
                start_sample=start,
                end_sample=end,
                sample_rate_hz=recording.sample_rate_hz,
                samples=recording.samples[start:end],
            )
        )
    return candidates
