from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib import error, request

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.base64_ingest_service import Base64IngestService

logger = logging.getLogger(__name__)
settings = get_settings()


class ExternalFetchService:
    def __init__(self) -> None:
        self.base64_ingest = Base64IngestService()

    def _build_headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if settings.EXTERNAL_FETCH_API_KEY:
            headers["Authorization"] = f"Bearer {settings.EXTERNAL_FETCH_API_KEY}"
        return headers

    def _normalize_case_key(self, case_type: str, case_no: str, case_year: int | str) -> str:
        ctype = re.sub(r"[^A-Za-z0-9]+", "", str(case_type or "")).upper()
        cno = re.sub(r"[^A-Za-z0-9]+", "", str(case_no or "")).upper()
        cyear = re.sub(r"[^0-9]+", "", str(case_year or ""))
        return f"{ctype}-{cno}-{cyear}".strip("-")

    def fetch_payload(self) -> dict:
        if not settings.EXTERNAL_FETCH_URL:
            raise RuntimeError("EXTERNAL_FETCH_URL is not configured")

        req = request.Request(
            url=settings.EXTERNAL_FETCH_URL,
            headers=self._build_headers(),
            method="GET",
        )

        try:
            with request.urlopen(req, timeout=settings.EXTERNAL_FETCH_TIMEOUT_SECONDS) as resp:
                status_code = getattr(resp, "status", None) or resp.getcode()
                body = resp.read().decode("utf-8", errors="ignore")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
            raise RuntimeError(f"External API HTTP error: {exc.code} {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"External API request failed: {exc}") from exc

        if int(status_code) != 200:
            raise RuntimeError(f"External API returned non-200 status: {status_code}")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("External API returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("External API payload must be a JSON object")
        return payload

    def extract_items(self, payload: dict) -> list[dict]:
        data = payload.get("data")
        if data is None:
            return []
        if not isinstance(data, list):
            raise RuntimeError("External API payload 'data' must be a list")
        return [item for item in data if isinstance(item, dict)]

    def validate_item(self, item: dict) -> None:
        required = ("case_type", "case_no", "case_year", "pdf")
        missing = [key for key in required if item.get(key) in (None, "")]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

    def ingest_items(self, db: Session, items: list[dict], overwrite: bool = False) -> list[dict]:
        results: list[dict] = []
        for item in items:
            case_key = self._normalize_case_key(
                str(item.get("case_type", "")),
                str(item.get("case_no", "")),
                item.get("case_year", ""),
            )
            ext_id = item.get("id")

            try:
                self.validate_item(item)
                ingest_result = self.base64_ingest.ingest_one(
                    db,
                    case_type=str(item["case_type"]),
                    case_no=str(item["case_no"]),
                    case_year=int(item["case_year"]),
                    base64_pdf=str(item["pdf"]),
                    overwrite=overwrite,
                    source_system=settings.EXTERNAL_FETCH_SOURCE_SYSTEM,
                )

                results.append(
                    {
                        "external_id": ext_id,
                        "case_key": case_key,
                        **ingest_result,
                    }
                )
            except Exception as exc:
                logger.exception("External item ingest failed case_key=%s external_id=%s", case_key, ext_id)
                results.append(
                    {
                        "external_id": ext_id,
                        "case_key": case_key,
                        "status": "failed",
                        "document_id": None,
                        "error": str(exc),
                    }
                )
        return results

    def fetch_and_ingest(self, db: Session, overwrite: bool = False, limit: int | None = None) -> dict:
        logger.info("Starting external fetch and ingest")

        payload = self.fetch_payload()
        items = self.extract_items(payload)

        if limit is not None and limit > 0:
            items = items[:limit]

        batch_size = max(1, int(settings.EXTERNAL_FETCH_BATCH_SIZE))
        all_results: list[dict] = []

        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            logger.info("Processing external batch chunk size=%s offset=%s", len(chunk), i)
            all_results.extend(self.ingest_items(db, chunk, overwrite=overwrite))

        total_received = len(items)
        total_processed = len(all_results)
        total_queued = sum(1 for r in all_results if r.get("status") == "queued")
        total_skipped = sum(1 for r in all_results if r.get("status") == "skipped_duplicate")
        total_failed = sum(1 for r in all_results if r.get("status") in {"failed", "enqueue_failed"})

        summary = {
            "total_received": total_received,
            "total_processed": total_processed,
            "total_queued": total_queued,
            "total_skipped": total_skipped,
            "total_failed": total_failed,
        }

        logger.info("External fetch summary: %s", summary)
        return {
            "ok": total_failed == 0,
            "message": "external fetch completed",
            "summary": summary,
            "items": all_results,
        }
