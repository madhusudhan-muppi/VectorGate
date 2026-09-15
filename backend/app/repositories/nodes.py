"""Node persistence operations."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Detection, Node


def create_node(db: Session, node: Node) -> Node:
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def get_node(db: Session, node_id: str) -> Node | None:
    return db.get(Node, node_id)


def list_nodes(db: Session) -> list[Node]:
    return list(db.scalars(select(Node).order_by(Node.node_id)))


def node_summary(db: Session, node_id: str) -> tuple[int, datetime | None]:
    count, latest = db.execute(
        select(func.count(Detection.id), func.max(Detection.recorded_at)).where(
            Detection.node_id == node_id
        )
    ).one()
    return int(count), latest
