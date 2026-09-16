"""High-level continuous-recording to flight-event analysis pipeline."""

from __future__ import annotations

from .analysis import extract_features
from .events import EventDetectionConfig, detect_events
from software.data.models import FlightEventResult, SensorRecording


def analyze_sensor_recording(
    recording: SensorRecording,
    detector_config: EventDetectionConfig | None = None,
    *,
    band_low_hz: float = 80.0,
    band_high_hz: float = 2000.0,
) -> list[FlightEventResult]:
    """Detect candidate events and run the existing Stage 1 DSP on each."""
    candidates = detect_events(recording, detector_config)
    results: list[FlightEventResult] = []
    for candidate in candidates:
        features, _ = extract_features(
            candidate.samples,
            recording.sample_rate_hz,
            band_low_hz=band_low_hz,
            band_high_hz=band_high_hz,
        )
        results.append(
            FlightEventResult(
                start_sample=candidate.start_sample,
                end_sample=candidate.end_sample,
                start_time_seconds=candidate.start_time_seconds,
                end_time_seconds=candidate.end_time_seconds,
                duration_seconds=candidate.duration_seconds,
                samples=candidate.samples,
                features=features,
                source=recording.source,
                node_id=recording.node_id,
                temperature_c=recording.temperature_c,
                humidity_percent=recording.humidity_percent,
            )
        )
    return results


def analyze_whole_recording(
    recording: SensorRecording,
    *,
    band_low_hz: float = 80.0,
    band_high_hz: float = 2000.0,
) -> FlightEventResult:
    """Run the Stage 1 DSP over the entire recording, skipping event detection.

    :func:`analyze_sensor_recording` looks for a burst standing above a quiet
    background, which is what an insect crossing the gate produces. Some inputs
    are continuous instead -- a chopper wheel, an LED driven at a fixed
    frequency, or a library clip that is wingbeat from end to end. For those,
    frame RMS is constant, the detector correctly finds nothing, and the useful
    thing to do is analyse the whole recording as one event.

    This validates the sensing and DSP chain. It is not evidence that an insect
    was present.
    """
    features, _ = extract_features(
        recording.samples,
        recording.sample_rate_hz,
        band_low_hz=band_low_hz,
        band_high_hz=band_high_hz,
    )
    count = len(recording.samples)
    duration = count / recording.sample_rate_hz
    return FlightEventResult(
        start_sample=0,
        end_sample=count,
        start_time_seconds=0.0,
        end_time_seconds=duration,
        duration_seconds=duration,
        samples=recording.samples,
        features=features,
        source=recording.source,
        node_id=recording.node_id,
        temperature_c=recording.temperature_c,
        humidity_percent=recording.humidity_percent,
    )
