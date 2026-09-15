"""Dashboard-ready aggregate and map data routes."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Detection, Node
from ..repositories.detections import aggregate_counts, latest_detection, map_rows
from ..repositories.nodes import get_node
from ..schemas import MapNodeResponse, SummaryResponse
from ..services.time import utc_now

router = APIRouter(tags=["summary"])


@router.get("/stats/summary", response_model=SummaryResponse)
def summary(db: Session = Depends(get_db)) -> SummaryResponse:
    now = utc_now()
    total_nodes = int(db.scalar(select(func.count(Node.node_id))) or 0)
    active_nodes = int(db.scalar(select(func.count(Node.node_id)).where(Node.active.is_(True))) or 0)
    total_detections = aggregate_counts(db)
    unknown = int(db.scalar(select(func.count(Detection.id)).where(Detection.predicted_class.is_(None))) or 0)
    return SummaryResponse(
        total_nodes=total_nodes,
        active_nodes=active_nodes,
        total_detections=total_detections,
        detections_last_hour=aggregate_counts(db, now - timedelta(hours=1)),
        detections_last_24h=aggregate_counts(db, now - timedelta(hours=24)),
        unknown_detections=unknown,
        latest_detection_at=latest_detection(db),
    )


@router.get("/map/nodes", response_model=list[MapNodeResponse])
def map_nodes(db: Session = Depends(get_db)) -> list[MapNodeResponse]:
    since = utc_now() - timedelta(hours=24)
    return [
        MapNodeResponse(
            node_id=node.node_id,
            name=node.name,
            latitude=node.latitude,
            longitude=node.longitude,
            location_label=node.location_label,
            active=node.active,
            recent_detection_count=count,
            latest_detection_at=latest,
        )
        for node, count, latest in map_rows(db, since)
    ]
