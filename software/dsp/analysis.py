"""FFT analysis and extensible flight-feature extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .preprocess import apply_hann_window, as_float_array, band_mask, remove_dc


@dataclass(frozen=True)
class SpectralAnalysis:
    """One-sided, amplitude-corrected FFT results."""

    frequencies_hz: np.ndarray
    magnitudes: np.ndarray
    dominant_frequency_hz: float
    dominant_magnitude: float
    band_low_hz: float
    band_high_hz: float
    window: np.ndarray


@dataclass(frozen=True)
class FeatureVector:
    """Features extracted from one waveform event.

    Harmonic ratios are the magnitudes at the nearest FFT bins to 2f and 3f,
    divided by the fundamental-bin magnitude. SNR compares energy in narrow
    bins around f, 2f, and 3f with the remaining energy in the configured band.
    This is a practical spectral estimate, not a calibrated sensor noise model.
    """

    dominant_frequency_hz: float
    dominant_magnitude: float
    second_harmonic_ratio: float
    third_harmonic_ratio: float
    rms: float
    peak_to_peak: float
    spectral_energy: float
    estimated_snr_db: float

    def as_dict(self) -> dict[str, float]:
        """Return a serializable mapping for later transport to a backend."""
        return asdict(self)


def compute_spectrum(
    samples: np.ndarray | list[float],
    sample_rate: float,
    band_low_hz: float = 80.0,
    band_high_hz: float = 2000.0,
) -> SpectralAnalysis:
    """Compute a one-sided Hann-windowed FFT and its dominant band frequency."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    array = remove_dc(as_float_array(samples))
    windowed, window = apply_hann_window(array)
    frequencies = np.fft.rfftfreq(array.size, d=1.0 / sample_rate)
    spectrum = np.fft.rfft(windowed)
    magnitudes = (2.0 * np.abs(spectrum)) / np.sum(window)
    if magnitudes.size:
        magnitudes[0] /= 2.0

    mask = band_mask(frequencies, band_low_hz, min(band_high_hz, sample_rate / 2.0))
    if not np.any(mask):
        raise ValueError("analysis band does not contain FFT bins")
    band_indices = np.flatnonzero(mask)
    dominant_index = band_indices[np.argmax(magnitudes[mask])]
    return SpectralAnalysis(
        frequencies_hz=frequencies,
        magnitudes=magnitudes,
        dominant_frequency_hz=float(frequencies[dominant_index]),
        dominant_magnitude=float(magnitudes[dominant_index]),
        band_low_hz=band_low_hz,
        band_high_hz=min(band_high_hz, sample_rate / 2.0),
        window=window,
    )


def _nearest_magnitude(spectrum: SpectralAnalysis, frequency_hz: float) -> float:
    index = int(np.argmin(np.abs(spectrum.frequencies_hz - frequency_hz)))
    return float(spectrum.magnitudes[index])


def _estimate_snr_db(spectrum: SpectralAnalysis, dominant_frequency_hz: float) -> float:
    band = band_mask(
        spectrum.frequencies_hz,
        spectrum.band_low_hz,
        spectrum.band_high_hz,
    )
    bin_spacing = spectrum.frequencies_hz[1] - spectrum.frequencies_hz[0]
    signal_mask = np.zeros_like(band)
    for harmonic in (1, 2, 3):
        center = harmonic * dominant_frequency_hz
        signal_mask |= np.abs(spectrum.frequencies_hz - center) <= max(bin_spacing * 1.5, 5.0)
    signal_energy = float(np.sum(np.square(spectrum.magnitudes[band & signal_mask])))
    noise_energy = float(np.sum(np.square(spectrum.magnitudes[band & ~signal_mask])))
    if noise_energy == 0:
        return float("inf")
    if signal_energy == 0:
        return float("-inf")
    return float(10.0 * np.log10(signal_energy / noise_energy))


def extract_features(
    samples: np.ndarray | list[float],
    sample_rate: float,
    band_low_hz: float = 80.0,
    band_high_hz: float = 2000.0,
) -> tuple[FeatureVector, SpectralAnalysis]:
    """Extract the current feature vector and retain the spectrum for plotting.

    The tuple keeps plotting and future quality diagnostics from recomputing the
    FFT. Additional event metadata can be added to ``FeatureVector`` later
    without coupling this API to any particular input source.
    """
    array = remove_dc(as_float_array(samples))
    spectrum = compute_spectrum(array, sample_rate, band_low_hz, band_high_hz)
    fundamental = spectrum.dominant_magnitude
    return FeatureVector(
        dominant_frequency_hz=spectrum.dominant_frequency_hz,
        dominant_magnitude=fundamental,
        second_harmonic_ratio=_nearest_magnitude(
            spectrum, 2.0 * spectrum.dominant_frequency_hz
        ) / fundamental if fundamental else 0.0,
        third_harmonic_ratio=_nearest_magnitude(
            spectrum, 3.0 * spectrum.dominant_frequency_hz
        ) / fundamental if fundamental else 0.0,
        rms=float(np.sqrt(np.mean(np.square(array)))),
        peak_to_peak=float(np.ptp(array)),
        spectral_energy=float(np.sum(np.square(spectrum.magnitudes))),
        estimated_snr_db=_estimate_snr_db(spectrum, spectrum.dominant_frequency_hz),
    ), spectrum


def feature_dict(
    samples: np.ndarray | list[float], sample_rate: float, **kwargs: Any
) -> dict[str, float]:
    """Convenience adapter for callers that need a dictionary payload."""
    features, _ = extract_features(samples, sample_rate, **kwargs)
    return features.as_dict()
