"""Run the Stage 1 synthetic signal and save diagnostic plots."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from software.dsp.analysis import extract_features
from software.dsp.signal import generate_waveform


def run_demo(output_dir: Path) -> tuple[float, float]:
    """Generate the demonstration event, print features, and save two plots."""
    sample_rate = 10_000.0
    injected_frequency = 500.0
    rng = np.random.default_rng(20260915)
    time, waveform = generate_waveform(
        sample_rate=sample_rate,
        duration=0.75,
        fundamental_frequency=injected_frequency,
        amplitude=1.0,
        harmonic_amplitudes={2: 0.30, 3: 0.12},
        noise_level=0.08,
        dc_offset=0.20,
        rng=rng,
    )
    features, spectrum = extract_features(waveform, sample_rate)
    error = abs(features.dominant_frequency_hz - injected_frequency)

    output_dir.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(10, 4))
    axis.plot(time, waveform, linewidth=0.8)
    axis.set(title="VectorGate synthetic optical waveform", xlabel="Time (s)", ylabel="Amplitude")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "waveform.png", dpi=150)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 4))
    band = (spectrum.frequencies_hz >= 80.0) & (spectrum.frequencies_hz <= 2000.0)
    axis.plot(spectrum.frequencies_hz[band], spectrum.magnitudes[band], linewidth=0.9)
    axis.axvline(
        features.dominant_frequency_hz,
        color="tab:red",
        linestyle="--",
        label=f"Detected: {features.dominant_frequency_hz:.2f} Hz",
    )
    axis.set(title="VectorGate one-sided magnitude spectrum", xlabel="Frequency (Hz)", ylabel="Magnitude")
    axis.legend()
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "spectrum.png", dpi=150)
    plt.close(fig)

    print("VectorGate DSP Demo")
    print("-------------------")
    print(f"Injected fundamental: {injected_frequency:.2f} Hz")
    print(f"Detected dominant:    {features.dominant_frequency_hz:.2f} Hz")
    print(f"Error:                {error:.2f} Hz")
    print("\nExtracted features:")
    for name, value in features.as_dict().items():
        print(f"  {name}: {value:.4f}")
    print(f"\nPlots saved to: {output_dir.resolve()}")

    return features.dominant_frequency_hz, error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="directory for waveform.png and spectrum.png",
    )
    args = parser.parse_args()
    run_demo(args.output_dir)


if __name__ == "__main__":
    main()
