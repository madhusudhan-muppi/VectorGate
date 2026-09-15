"""SQLAlchemy persistence models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, UTCDateTime


class Node(Base):
    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location_label: Mapped[str] = mapped_column(String(300), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    detections: Mapped[list[Detection]] = relationship(back_populates="node", cascade="all, delete-orphan")


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.node_id"), index=True, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    dominant_frequency_hz: Mapped[float] = mapped_column(Float, nullable=False)
    event_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    dominant_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    second_harmonic_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    third_harmonic_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    rms: Mapped[float] = mapped_column(Float, nullable=False)
    peak_to_peak: Mapped[float] = mapped_column(Float, nullable=False)
    spectral_energy: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_snr_db: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    node: Mapped[Node] = relationship(back_populates="detections")
