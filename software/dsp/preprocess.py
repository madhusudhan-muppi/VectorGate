"""Small, reusable preprocessing operations for waveform analysis."""

from __future__ import annotations

import numpy as np


def as_float_array(samples: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    """Convert samples to a one-dimensional floating-point NumPy array."""
    array = np.asarray(samples, dtype=float)
    if array.ndim != 1 or array.size < 2:
        raise ValueError("samples must be a one-dimensional array with at least two values")
    if not np.all(np.isfinite(array)):
        raise ValueError("samples must contain only finite values")
    return array


def remove_dc(samples: np.ndarray) -> np.ndarray:
    """Remove the measured mean, including sensor bias and optical DC level."""
    array = as_float_array(samples)
    return array - np.mean(array)


def apply_hann_window(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply a Hann window and return both the windowed samples and window."""
    array = as_float_array(samples)
    window = np.hanning(array.size)
    return array * window, window


def band_mask(
    frequencies: np.ndarray,
    low_hz: float,
    high_hz: float,
) -> np.ndarray:
    """Return the mask for an inclusive frequency analysis band."""
    if low_hz < 0 or high_hz <= low_hz:
        raise ValueError("frequency band must satisfy 0 <= low_hz < high_hz")
    return (frequencies >= low_hz) & (frequencies <= high_hz)
