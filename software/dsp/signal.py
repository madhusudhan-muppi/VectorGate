"""Synthetic optical waveform sources used to validate the DSP chain."""

from __future__ import annotations

from typing import Mapping

import numpy as np


def generate_waveform(
    sample_rate: float,
    duration: float,
    fundamental_frequency: float,
    amplitude: float = 1.0,
    harmonic_amplitudes: Mapping[int, float] | None = None,
    noise_level: float = 0.0,
    dc_offset: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic optical wingbeat-like waveform.

    Harmonic amplitudes are specified relative to ``amplitude`` using harmonic
    numbers as keys, for example ``{2: 0.35, 3: 0.15}``. The result is a DSP
    fixture, not a biological model or a species classifier.
    """
    if sample_rate <= 0 or duration <= 0 or fundamental_frequency <= 0:
        raise ValueError("sample_rate, duration, and frequency must be positive")
    if amplitude < 0 or noise_level < 0:
        raise ValueError("amplitude and noise_level must be non-negative")
    if fundamental_frequency >= sample_rate / 2:
        raise ValueError("fundamental_frequency must be below the Nyquist frequency")

    sample_count = int(round(sample_rate * duration))
    if sample_count < 2:
        raise ValueError("duration must produce at least two samples")

    time = np.arange(sample_count, dtype=float) / sample_rate
    waveform = amplitude * np.sin(2.0 * np.pi * fundamental_frequency * time)
    for harmonic, relative_amplitude in (harmonic_amplitudes or {}).items():
        if harmonic < 2 or int(harmonic) != harmonic:
            raise ValueError("harmonic numbers must be integers greater than or equal to 2")
        if relative_amplitude < 0:
            raise ValueError("harmonic amplitudes must be non-negative")
        frequency = harmonic * fundamental_frequency
        if frequency >= sample_rate / 2:
            raise ValueError("harmonic frequency must be below the Nyquist frequency")
        waveform += amplitude * relative_amplitude * np.sin(2.0 * np.pi * frequency * time)

    if noise_level:
        generator = rng if rng is not None else np.random.default_rng()
        waveform += generator.normal(0.0, noise_level, size=sample_count)

    return time, waveform + dc_offset
