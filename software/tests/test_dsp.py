"""Behavior tests for the Stage 1 DSP chain."""

import numpy as np
import pytest

from software.dsp.analysis import extract_features
from software.dsp.signal import generate_waveform


SAMPLE_RATE = 10_000.0
DURATION = 0.5


def analyze(frequency: float, noise_level: float = 0.0, dc_offset: float = 0.0):
    _, waveform = generate_waveform(
        sample_rate=SAMPLE_RATE,
        duration=DURATION,
        fundamental_frequency=frequency,
        harmonic_amplitudes={2: 0.30, 3: 0.12},
        noise_level=noise_level,
        dc_offset=dc_offset,
        rng=np.random.default_rng(7),
    )
    return extract_features(waveform, SAMPLE_RATE)[0]


@pytest.mark.parametrize("frequency", [500.0, 350.0, 700.0])
def test_detects_expected_frequency(frequency: float):
    features = analyze(frequency)
    assert abs(features.dominant_frequency_hz - frequency) <= SAMPLE_RATE / (SAMPLE_RATE * DURATION)


def test_noisy_500_hz_signal_remains_detectable():
    features = analyze(500.0, noise_level=0.15)
    assert abs(features.dominant_frequency_hz - 500.0) <= 2.0
    assert features.estimated_snr_db > 5.0


def test_dc_offset_does_not_change_frequency_detection():
    baseline = analyze(500.0, noise_level=0.05)
    offset = analyze(500.0, noise_level=0.05, dc_offset=25.0)
    assert offset.dominant_frequency_hz == baseline.dominant_frequency_hz


def test_normal_harmonics_do_not_replace_fundamental():
    features = analyze(500.0)
    assert features.dominant_frequency_hz == 500.0
    assert 0.2 < features.second_harmonic_ratio < 0.4
    assert 0.05 < features.third_harmonic_ratio < 0.2


def test_feature_payload_contains_required_fields():
    features = analyze(500.0)
    assert set(features.as_dict()) == {
        "dominant_frequency_hz",
        "dominant_magnitude",
        "second_harmonic_ratio",
        "third_harmonic_ratio",
        "rms",
        "peak_to_peak",
        "spectral_energy",
        "estimated_snr_db",
    }
