from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.queue_item import QueueItem


ACTIVE_STATUSES = {"PENDING", "RUNNING"}
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


class QueueService:
    def enqueue_task(
        self,
        db: Session,
        *,
        queue_name: str,
        document_id: int,
        task_id: str,
        priority: int = 100,
    ) -> QueueItem:
        row = QueueItem(
            queue_name=queue_name,
            document_id=document_id,
            status="PENDING",
            priority=priority,
            attempts=0,
            worker_id=task_id,
            heartbeat_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def mark_started(self, db: Session, task_id: str) -> None:
        row = self._get_by_task_id(db, task_id)
        if not row:
            return

        row.status = "RUNNING"
        row.attempts = int(row.attempts or 0) + 1
        row.heartbeat_at = datetime.utcnow()
        db.add(row)
        db.commit()

    def touch(self, db: Session, task_id: str) -> None:
        row = self._get_by_task_id(db, task_id)
        if not row:
            return

        row.heartbeat_at = datetime.utcnow()
        db.add(row)
        db.commit()

    def mark_terminal(self, db: Session, task_id: str, status: str) -> None:
        row = self._get_by_task_id(db, task_id)
        if not row:
            return

        row.status = status
        row.heartbeat_at = datetime.utcnow()
        db.add(row)
        db.commit()

    def active_for_document(self, db: Session, document_id: int) -> list[QueueItem]:
        stmt = (
            select(QueueItem)
            .where(
                and_(
                    QueueItem.document_id == document_id,
                    QueueItem.status.in_(ACTIVE_STATUSES),
                )
            )
            .order_by(QueueItem.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    def has_active_for_document(self, db: Session, document_id: int) -> bool:
        return len(self.active_for_document(db, document_id)) > 0

    def list_active(self, db: Session) -> list[QueueItem]:
        stmt = (
            select(QueueItem)
            .where(QueueItem.status.in_(ACTIVE_STATUSES))
            .order_by(QueueItem.created_at.desc())
        )
        return list(db.scalars(stmt).all())

    def mark_cancelled_for_document(self, db: Session, document_id: int) -> list[QueueItem]:
        rows = self.active_for_document(db, document_id)
        now = datetime.utcnow()

        for row in rows:
            row.status = "CANCELLED"
            row.heartbeat_at = now
            db.add(row)

        db.commit()
        return rows

    def cancel_stale_for_document(self, db: Session, document_id: int, stale_seconds: int = 180) -> list[QueueItem]:
        rows = self.active_for_document(db, document_id)
        if not rows:
            return []

        now = datetime.utcnow()
        threshold = now - timedelta(seconds=stale_seconds)
        stale_rows: list[QueueItem] = []

        for row in rows:
            hb = row.heartbeat_at
            if hb is None or hb <= threshold:
                row.status = "CANCELLED"
                row.heartbeat_at = now
                db.add(row)
                stale_rows.append(row)

        if stale_rows:
            db.commit()
        return stale_rows

    def clear_pending(self, db: Session) -> int:
        stmt = select(QueueItem).where(QueueItem.status == "PENDING")
        rows = list(db.scalars(stmt).all())
        count = len(rows)

        for row in rows:
            db.delete(row)

        db.commit()
        return count

    def _get_by_task_id(self, db: Session, task_id: str) -> QueueItem | None:
        stmt = select(QueueItem).where(QueueItem.worker_id == task_id).order_by(QueueItem.created_at.desc())
        return db.scalars(stmt).first()
