"""Reusable signal generation and DSP analysis components."""

from .analysis import FeatureVector, SpectralAnalysis, extract_features
from .events import EventDetectionConfig, detect_events
from .pipeline import analyze_sensor_recording
from .signal import generate_waveform

__all__ = [
    "FeatureVector",
    "SpectralAnalysis",
    "EventDetectionConfig",
    "analyze_sensor_recording",
    "detect_events",
    "extract_features",
    "generate_waveform",
]
