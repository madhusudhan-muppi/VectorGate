"""Detection persistence and aggregate query operations."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Detection, Node


def create_detection(db: Session, detection: Detection) -> Detection:
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection


def get_detection(db: Session, detection_id: int) -> Detection | None:
    return db.get(Detection, detection_id)


def list_detections(
    db: Session,
    *,
    node_id: str | None = None,
    limit: int = 100,
    since: datetime | None = None,
    predicted_class: str | None = None,
) -> list[Detection]:
    query = select(Detection).order_by(Detection.recorded_at.desc(), Detection.id.desc()).limit(limit)
    if node_id is not None:
        query = query.where(Detection.node_id == node_id)
    if since is not None:
        query = query.where(Detection.recorded_at >= since)
    if predicted_class is not None:
        query = query.where(Detection.predicted_class == predicted_class)
    return list(db.scalars(query))


def aggregate_counts(db: Session, since: datetime | None = None) -> int:
    query = select(func.count(Detection.id))
    if since is not None:
        query = query.where(Detection.recorded_at >= since)
    return int(db.scalar(query) or 0)


def latest_detection(db: Session) -> datetime | None:
    return db.scalar(select(func.max(Detection.recorded_at)))


def count_for_node_since(db: Session, node_id: str, since: datetime | None = None) -> int:
    query = select(func.count(Detection.id)).where(Detection.node_id == node_id)
    if since is not None:
        query = query.where(Detection.recorded_at >= since)
    return int(db.scalar(query) or 0)


def latest_for_node(db: Session, node_id: str) -> datetime | None:
    return db.scalar(select(func.max(Detection.recorded_at)).where(Detection.node_id == node_id))


def grouped_activity(
    db: Session,
    node_id: str,
    since: datetime,
    until: datetime,
    bucket_seconds: int,
) -> list[tuple[datetime, int]]:
    detections = db.scalars(
        select(Detection.recorded_at)
        .where(
            Detection.node_id == node_id,
            Detection.recorded_at >= since,
            Detection.recorded_at < until,
        )
        .order_by(Detection.recorded_at)
    )
    buckets: dict[datetime, int] = {}
    for recorded_at in detections:
        elapsed = int((recorded_at - since).total_seconds())
        bucket_index = max(0, elapsed // bucket_seconds)
        bucket_start = since + timedelta(seconds=bucket_index * bucket_seconds)
        buckets[bucket_start] = buckets.get(bucket_start, 0) + 1
    return sorted(buckets.items())


def map_rows(db: Session, since: datetime) -> list[tuple[Node, int, datetime | None]]:
    nodes = list(db.scalars(select(Node).order_by(Node.node_id)))
    return [(node, count_for_node_since(db, node.node_id, since), latest_for_node(db, node.node_id)) for node in nodes]
