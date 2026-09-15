"""Optional, explicitly synthetic VectorGate classification subsystem."""

from .features import FEATURE_NAMES, feature_vector_from_detection, feature_vector_from_event
from .model import ClassificationResult, DemoClassifier, classifier_status

__all__ = [
    "FEATURE_NAMES",
    "ClassificationResult",
    "DemoClassifier",
    "classifier_status",
    "feature_vector_from_detection",
    "feature_vector_from_event",
]
