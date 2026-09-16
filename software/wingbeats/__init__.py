"""WINGBEATS dataset handling: manifest, session-aware sampling, features, training.

The WINGBEATS corpus (Potamitis & Rigakis, IEEE Sensors Journal 16(15), 2016)
was recorded optically -- an IR beam, a mosquito partially occluding it, a
photodetector -- which is the same sensing modality as a VectorGate node. That
is why it is used here in preference to larger acoustic mosquito datasets.

This package is deliberately separate from :mod:`software.classifier`, which
carries the live 8-feature contract used by the backend bridge. Unifying the
two feature definitions is a follow-up; doing it here would break the running
API mid-build.
"""
