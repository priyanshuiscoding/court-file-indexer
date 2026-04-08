from datetime import datetime
from sqlalchemy.orm import Session
from app.models.processing_log import ProcessingLog


class LogService:
    def create_log(
        self,
        db: Session,
        *,
        document_id: int | None,
        step_name: str,
        status: str,
        message: str | None = None,
        metadata_json: str | None = None,
    ) -> ProcessingLog:
        log = ProcessingLog(
            document_id=document_id,
            step_name=step_name,
            status=status,
            message=message,
            metadata_json=metadata_json,
            started_at=datetime.utcnow(),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def finish_log(self, db: Session, log: ProcessingLog, status: str, message: str | None = None) -> ProcessingLog:
        finished = datetime.utcnow()
        log.finished_at = finished
        log.status = status
        log.message = message or log.message
        log.duration_ms = int((finished - log.started_at).total_seconds() * 1000)
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
