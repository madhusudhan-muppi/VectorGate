"""Optical-wingbeat feature extraction.

The feature set follows the Rothamsted optical-wingbeat specification
(amplitude statistics, dominant and fundamental frequency, harmonic ratios,
spectral/temporal entropies, bioacoustic band indices, with log and sqrt
transforms on the skewed distributions), with four deliberate corrections.

Harmonics are referenced to the fundamental, not the dominant peak. Optical
occlusion signals frequently have a harmonic louder than the fundamental, which
is the whole reason the autocorrelation estimate exists; referencing the
harmonic ladder to the dominant peak throws that away.

Harmonics above Nyquist are marked missing, not zero. WINGBEATS is sampled at
8 kHz, so a 900 Hz fundamental has no measurable 5th harmonic. Silently
recording 0.0 makes the upper ratios a disguised function of the fundamental
rather than a measurement, which a tree model will happily exploit.

An 80 Hz high-pass precedes every feature, matching the 80-2000 Hz analysis
band in the hardware/software contract and removing the body-oscillation and
drift content below the wingbeat fundamental. The lowest bioacoustic band is
therefore 80-300 Hz where Rothamsted specify 50-300 Hz.

Temperature and humidity are never extracted. They appear in some WINGBEATS
filenames, but their *presence* alone separates three of the six species
(C. pipiens 93% labelled, Ae. aegypti 0%), so both the values and their
missingness are label leaks in this corpus.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, get_window, sosfiltfilt

HIGHPASS_HZ = 80.0
HIGHPASS_ORDER = 4
F0_MIN_HZ = 150.0
F0_MAX_HZ = 1000.0
N_HARMONICS = 5
HARMONIC_HALFWIDTH_HZ = 25.0
BIOACOUSTIC_BANDS = ((80, 300), (80, 1000), (200, 3000), (300, 700))
ROLLOFF_FRACTION = 0.85
MIN_SAMPLES = 512

#: Features whose value depends on recording gain and on how close the insect
#: flew to the sensor. They do not transfer to different hardware, so the
#: trainer also fits a model without them.
SCALE_DEPENDENT = (
    "log_max_amp",
    "log_rms",
    "log_power",
    "log_iqr_amp",
)


def _band_indices(freqs: np.ndarray, low: float, high: float) -> np.ndarray:
    return (freqs >= low) & (freqs <= high)


def extract_from_samples(samples: np.ndarray, sample_rate: float) -> dict[str, float] | None:
    """Return the feature dictionary for one waveform, or ``None`` if unusable.

    This is the single extraction path. Training reads WAVs through
    :func:`extract`; the API extracts from sample batches sent by a node. Both
    land here, so on-device and server-side features cannot silently diverge.
    """
    raw = np.asarray(samples)
    if raw.ndim > 1:
        raw = raw.mean(axis=1)
    signal = np.asarray(raw, dtype=np.float64)
    if signal.size < MIN_SAMPLES:
        return None

    nyquist = sample_rate / 2.0
    if HIGHPASS_HZ >= nyquist:
        return None

    signal = signal - signal.mean()
    sos = butter(HIGHPASS_ORDER, HIGHPASS_HZ / nyquist, btype="highpass", output="sos")
    signal = sosfiltfilt(sos, signal)

    peak = float(np.abs(signal).max())
    rms = float(np.sqrt(np.mean(signal**2)))
    if peak < 1e-9 or rms < 1e-12:
        return None

    n = signal.size
    duration = n / sample_rate
    crest = peak / rms
    iqr_amp = float(np.subtract(*np.percentile(signal, [75, 25])))
    zcr = float(np.mean(np.abs(np.diff(np.sign(signal)))) / 2.0)

    window = get_window("hann", n)
    spectrum = np.abs(np.fft.rfft(signal * window))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    psd = spectrum**2
    total_power = float(psd.sum()) + 1e-12
    normalised = psd / total_power

    search = _band_indices(freqs, F0_MIN_HZ, min(F0_MAX_HZ, nyquist))
    if not search.any():
        return None
    dominant = float(freqs[search][np.argmax(psd[search])])

    # Fundamental by autocorrelation: robust when a harmonic outranks F0.
    autocorr = np.correlate(signal, signal, mode="full")[n - 1 :]
    autocorr = autocorr / (autocorr[0] + 1e-12)
    lag_low = max(1, int(sample_rate / min(F0_MAX_HZ, nyquist)))
    lag_high = min(n - 1, int(sample_rate / F0_MIN_HZ))
    if lag_high > lag_low + 2:
        segment = autocorr[lag_low:lag_high]
        fundamental = sample_rate / float(lag_low + int(np.argmax(segment)))
        f0_strength = float(segment.max())
    else:
        fundamental, f0_strength = dominant, 0.0

    def band_energy(centre: float) -> float:
        selector = _band_indices(
            freqs, centre - HARMONIC_HALFWIDTH_HZ, centre + HARMONIC_HALFWIDTH_HZ
        )
        return float(psd[selector].sum()) if selector.any() else 0.0

    # Harmonic ladder anchored on the fundamental, truncated at Nyquist.
    base = band_energy(fundamental) + 1e-12
    harmonics: dict[str, float] = {}
    n_valid = 0
    for k in range(2, N_HARMONICS + 1):
        centre = fundamental * k
        if centre + HARMONIC_HALFWIDTH_HZ > nyquist:
            harmonics[f"harm{k}_ratio"] = np.nan
        else:
            harmonics[f"harm{k}_ratio"] = band_energy(centre) / base
            n_valid += 1

    centroid = float((freqs * normalised).sum())
    spread = float(np.sqrt((((freqs - centroid) ** 2) * normalised).sum()))
    cumulative = np.cumsum(normalised)
    rolloff = float(freqs[min(int(np.searchsorted(cumulative, ROLLOFF_FRACTION)), freqs.size - 1)])
    flatness = float(np.exp(np.mean(np.log(psd + 1e-12))) / (psd.mean() + 1e-12))
    spectral_entropy = float(
        -(normalised * np.log(normalised + 1e-12)).sum() / np.log(normalised.size)
    )

    envelope = np.abs(signal)
    envelope = envelope / (envelope.sum() + 1e-12)
    temporal_entropy = float(-(envelope * np.log(envelope + 1e-12)).sum() / np.log(n))

    row: dict[str, float] = {
        "duration_s": duration,
        "log_max_amp": float(np.log(peak)),
        "log_rms": float(np.log(rms)),
        "log_power": float(np.log(rms**2)),
        "log_iqr_amp": float(np.log(abs(iqr_amp) + 1e-12)),
        "log_crest_factor": float(np.log(crest)),
        "zcr": zcr,
        "dom_freq": dominant,
        "sqrt_dom_freq": float(np.sqrt(dominant)),
        "f0_hz": float(fundamental),
        "sqrt_f0": float(np.sqrt(fundamental)),
        "f0_strength": f0_strength,
        "f0_dom_ratio": float(fundamental / (dominant + 1e-12)),
        "spectral_centroid": centroid,
        "spectral_spread": spread,
        "spectral_rolloff": rolloff,
        "spectral_flatness": flatness,
        "spectral_entropy": spectral_entropy,
        "temporal_entropy": temporal_entropy,
        "acoustic_entropy": spectral_entropy * temporal_entropy,
        "n_harmonics_valid": float(n_valid),
    }
    row.update(harmonics)
    for low, high in BIOACOUSTIC_BANDS:
        selector = _band_indices(freqs, low, high)
        row[f"bio_{low}_{high}"] = float(psd[selector].sum() / total_power) if selector.any() else 0.0
    return row


def extract(path: str | Path) -> dict[str, float] | None:
    """Read one WAV file and extract its features."""
    try:
        sample_rate, raw = wavfile.read(path)
    except Exception:
        return None
    return extract_from_samples(raw, float(sample_rate))


def feature_names() -> tuple[str, ...]:
    """Feature column order, derived from the constants above."""
    names = [
        "duration_s",
        "log_max_amp",
        "log_rms",
        "log_power",
        "log_iqr_amp",
        "log_crest_factor",
        "zcr",
        "dom_freq",
        "sqrt_dom_freq",
        "f0_hz",
        "sqrt_f0",
        "f0_strength",
        "f0_dom_ratio",
        "spectral_centroid",
        "spectral_spread",
        "spectral_rolloff",
        "spectral_flatness",
        "spectral_entropy",
        "temporal_entropy",
        "acoustic_entropy",
        "n_harmonics_valid",
    ]
    names += [f"harm{k}_ratio" for k in range(2, N_HARMONICS + 1)]
    names += [f"bio_{low}_{high}" for low, high in BIOACOUSTIC_BANDS]
    return tuple(names)


def scale_invariant_names() -> tuple[str, ...]:
    """Feature columns that survive a change of sensor, gain and flight distance."""
    return tuple(name for name in feature_names() if name not in SCALE_DEPENDENT)
