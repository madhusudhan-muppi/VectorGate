"""Node registration and node activity routes."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Node
from ..repositories.detections import grouped_activity
from ..repositories.nodes import create_node, get_node, list_nodes, node_summary
from ..schemas import ActivityBucket, NodeCreate, NodeResponse, NodeSummary
from ..services.time import ensure_utc, utc_now

router = APIRouter(prefix="/nodes", tags=["nodes"])


@router.post("", response_model=NodeResponse, status_code=201)
def register_node(payload: NodeCreate, db: Session = Depends(get_db)) -> NodeResponse:
    node = Node(**payload.model_dump(), created_at=utc_now())
    try:
        create_node(db, node)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="node_id already exists") from exc
    return NodeResponse(**payload.model_dump(), created_at=node.created_at, recent_summary=NodeSummary(total_detections=0, latest_detection_at=None))


@router.get("", response_model=list[NodeResponse])
def get_nodes(db: Session = Depends(get_db)) -> list[NodeResponse]:
    response = []
    for node in list_nodes(db):
        count, latest = node_summary(db, node.node_id)
        response.append(NodeResponse.model_validate(node).model_copy(update={"recent_summary": NodeSummary(total_detections=count, latest_detection_at=latest)}))
    return response


@router.get("/{node_id}/activity", response_model=list[ActivityBucket])
def node_activity(
    node_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    bucket_seconds: int = Query(default=3600, ge=60, le=86400),
    db: Session = Depends(get_db),
) -> list[ActivityBucket]:
    if get_node(db, node_id) is None:
        raise HTTPException(status_code=404, detail="node not found")
    try:
        end = ensure_utc(until) if until else utc_now()
        start = ensure_utc(since) if since else end - timedelta(hours=24)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if end <= start:
        raise HTTPException(status_code=400, detail="until must be after since and timestamps must include timezone")
    return [ActivityBucket(bucket_start=bucket, count=count) for bucket, count in grouped_activity(db, node_id, start, end, bucket_seconds)]


@router.get("/{node_id}", response_model=NodeResponse)
def get_one_node(node_id: str, db: Session = Depends(get_db)) -> NodeResponse:
    node = get_node(db, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")
    count, latest = node_summary(db, node_id)
    return NodeResponse.model_validate(node).model_copy(update={"recent_summary": NodeSummary(total_detections=count, latest_detection_at=latest)})
