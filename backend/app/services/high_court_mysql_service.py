from __future__ import annotations

import logging
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtMySQLService:
    def _connect(self):
        if not settings.HC_MYSQL_HOST:
            raise RuntimeError("HC_MYSQL_HOST is not configured")
        if not settings.HC_MYSQL_USER:
            raise RuntimeError("HC_MYSQL_USER is not configured")
        if not settings.HC_MYSQL_PASSWORD:
            raise RuntimeError("HC_MYSQL_PASSWORD is not configured")

        return pymysql.connect(
            host=settings.HC_MYSQL_HOST,
            port=int(settings.HC_MYSQL_PORT),
            user=settings.HC_MYSQL_USER,
            password=settings.HC_MYSQL_PASSWORD,
            database=settings.HC_MYSQL_DB,
            cursorclass=DictCursor,
            connect_timeout=10,
            read_timeout=30,
            charset="utf8mb4",
        )

    def fetch_pending_rows(self, limit: int) -> list[dict[str, Any]]:
        table = settings.HC_MYSQL_TABLE or "mp_indexing_batch"
        db_name = settings.HC_MYSQL_DB or "Digitization"

        query = f"""
            SELECT *
            FROM `{db_name}`.`{table}`
            WHERE branch = 1
              AND completed = 0
              AND indexing_com_date = 0
              AND process_id = 1
              AND clean_fl_pdf_gen_dt = 0
            ORDER BY entry_dt ASC
            LIMIT %s
        """

        logger.info("Fetching pending High Court rows limit=%s", limit)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = list(cur.fetchall())

        logger.info("Fetched %s pending High Court rows", len(rows))
        return rows
