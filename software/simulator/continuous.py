"""Continuous synthetic recordings with smoothly embedded temporary events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np

from software.data.models import SensorRecording


@dataclass(frozen=True)
class SyntheticEvent:
    """Parameters for one temporary wingbeat-like event."""

    start_time_seconds: float
    duration_seconds: float
    fundamental_frequency_hz: float
    amplitude: float = 1.0
    harmonic_amplitudes: Mapping[int, float] = field(default_factory=dict)
    noise_level: float = 0.0


def generate_continuous_recording(
    sample_rate_hz: float,
    duration_seconds: float,
    events: list[SyntheticEvent],
    background_noise_level: float = 0.03,
    dc_offset: float = 0.0,
    rng: np.random.Generator | None = None,
    *,
    source: str = "synthetic-continuous",
    node_id: str | None = None,
    temperature_c: float | None = None,
    humidity_percent: float | None = None,
) -> SensorRecording:
    """Create background noise with cosine-ramped event envelopes.

    Event parameters describe a DSP fixture only. A 5% attack/release envelope
    prevents hard waveform discontinuities at event boundaries while keeping
    the event timing explicit.
    """
    if sample_rate_hz <= 0 or duration_seconds <= 0:
        raise ValueError("sample_rate_hz and duration_seconds must be positive")
    if background_noise_level < 0:
        raise ValueError("background_noise_level must be non-negative")
    sample_count = int(round(sample_rate_hz * duration_seconds))
    time = np.arange(sample_count, dtype=float) / sample_rate_hz
    generator = rng if rng is not None else np.random.default_rng()
    samples = generator.normal(0.0, background_noise_level, size=sample_count) + dc_offset

    for event in events:
        if event.start_time_seconds < 0 or event.duration_seconds <= 0:
            raise ValueError("event start must be non-negative and duration positive")
        if event.start_time_seconds + event.duration_seconds > duration_seconds:
            raise ValueError("event must fit within the recording")
        if event.fundamental_frequency_hz <= 0 or event.fundamental_frequency_hz >= sample_rate_hz / 2:
            raise ValueError("event frequency must be below the Nyquist frequency")
        if event.amplitude < 0 or event.noise_level < 0:
            raise ValueError("event amplitude and noise level must be non-negative")

        relative_time = time - event.start_time_seconds
        active = (relative_time >= 0) & (relative_time < event.duration_seconds)
        if not np.any(active):
            continue
        local_time = relative_time[active]
        waveform = np.sin(2.0 * np.pi * event.fundamental_frequency_hz * local_time)
        for harmonic, relative_amplitude in event.harmonic_amplitudes.items():
            if harmonic < 2 or int(harmonic) != harmonic or relative_amplitude < 0:
                raise ValueError("harmonics must be integer keys >= 2 with non-negative amplitudes")
            harmonic_frequency = harmonic * event.fundamental_frequency_hz
            if harmonic_frequency >= sample_rate_hz / 2:
                raise ValueError("event harmonic must be below the Nyquist frequency")
            waveform += relative_amplitude * np.sin(2.0 * np.pi * harmonic_frequency * local_time)

        ramp_duration = min(event.duration_seconds * 0.05, 0.03)
        envelope = np.ones_like(local_time)
        if ramp_duration > 0:
            envelope = np.minimum(
                1.0,
                np.minimum(local_time / ramp_duration, (event.duration_seconds - local_time) / ramp_duration),
            )
            envelope = np.clip(envelope, 0.0, 1.0)
        samples[active] += event.amplitude * envelope * waveform
        if event.noise_level:
            samples[active] += generator.normal(0.0, event.noise_level, size=active.sum())

    return SensorRecording(
        samples=samples,
        sample_rate_hz=sample_rate_hz,
        source=source,
        node_id=node_id,
        temperature_c=temperature_c,
        humidity_percent=humidity_percent,
    )
