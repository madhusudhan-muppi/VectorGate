"""Run the Stage 2 continuous event-detection demonstration."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from software.dsp.events import EventDetectionConfig
from software.dsp.pipeline import analyze_sensor_recording
from software.simulator.continuous import SyntheticEvent, generate_continuous_recording


def run_demo(output_dir: Path) -> list[float]:
    sample_rate = 10_000.0
    recording = generate_continuous_recording(
        sample_rate_hz=sample_rate,
        duration_seconds=5.0,
        background_noise_level=0.025,
        dc_offset=0.2,
        rng=np.random.default_rng(20260915),
        node_id="VG-SIM-01",
        temperature_c=24.5,
        humidity_percent=68.0,
        events=[
            SyntheticEvent(1.5, 0.25, 500.0, amplitude=0.8, harmonic_amplitudes={2: 0.3, 3: 0.12}),
            SyntheticEvent(3.0, 0.20, 350.0, amplitude=0.75, harmonic_amplitudes={2: 0.25, 3: 0.10}),
        ],
    )
    results = analyze_sensor_recording(recording, EventDetectionConfig())

    output_dir.mkdir(parents=True, exist_ok=True)
    time = np.arange(recording.samples.size) / recording.sample_rate_hz
    fig, axis = plt.subplots(figsize=(12, 4))
    axis.plot(time, recording.samples, linewidth=0.5, color="0.25")
    for result in results:
        axis.axvspan(result.start_time_seconds, result.end_time_seconds, color="tab:orange", alpha=0.3)
    axis.set(
        title="VectorGate continuous recording with detected events",
        xlabel="Time (s)",
        ylabel="Sensor amplitude",
    )
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "event_detection.png", dpi=150)
    plt.close(fig)

    print("VectorGate Event Detection Demo")
    print("-------------------------------")
    print(f"Recording duration: {recording.duration_seconds:.2f} s")
    print(f"Detected events: {len(results)}")
    for number, result in enumerate(results, start=1):
        injected = 500.0 if number == 1 else 350.0
        detected = result.features.dominant_frequency_hz
        print(f"\nEvent {number}")
        print(f"Start:              {result.start_time_seconds:.3f} s")
        print(f"End:                {result.end_time_seconds:.3f} s")
        print(f"Duration:           {result.duration_seconds:.3f} s")
        print(f"Dominant frequency: {detected:.2f} Hz")
        print(f"Frequency error:    {abs(detected - injected):.2f} Hz")
    print(f"\nPlots saved to: {output_dir.resolve()}")
    if len(results) != 2:
        raise RuntimeError(f"expected 2 synthetic events, detected {len(results)}")
    return [result.features.dominant_frequency_hz for result in results]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    run_demo(args.output_dir)


if __name__ == "__main__":
    main()
