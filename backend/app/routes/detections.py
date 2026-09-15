"""Detection ingestion and query routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Detection
from ..repositories.detections import create_detection, get_detection, list_detections
from ..repositories.nodes import get_node
from ..schemas import DetectionCreate, DetectionResponse
from ..services.time import ensure_utc, utc_now

router = APIRouter(prefix="/detections", tags=["detections"])


@router.post("", response_model=DetectionResponse, status_code=201)
def ingest_detection(payload: DetectionCreate, db: Session = Depends(get_db)) -> Detection:
    if get_node(db, payload.node_id) is None:
        raise HTTPException(status_code=404, detail="node not found")
    detection = Detection(**payload.model_dump(), received_at=utc_now())
    return create_detection(db, detection)


@router.get("", response_model=list[DetectionResponse])
def get_detections(
    node_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    since: datetime | None = None,
    predicted_class: str | None = None,
    db: Session = Depends(get_db),
) -> list[Detection]:
    if since is not None:
        try:
            since = ensure_utc(since)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return list_detections(db, node_id=node_id, limit=limit, since=since, predicted_class=predicted_class)


@router.get("/{detection_id}", response_model=DetectionResponse)
def get_one_detection(detection_id: int, db: Session = Depends(get_db)) -> Detection:
    detection = get_detection(db, detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="detection not found")
    return detection
