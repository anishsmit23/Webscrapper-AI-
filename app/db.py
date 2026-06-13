"""SQLite storage for enriched company profiles.

Repairs applied:
- #9  Single shared connection with WAL mode + threading lock for writes
- #10 Duplicate detection — skip re-insert if same URL was enriched within 24h
- #11 Pagination support via limit/offset
- #15 Structured logging
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "companies.db"
SEED_PATH = DATA_DIR / "seed_companies.json"

_conn: sqlite3.Connection | None = None
_write_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """Return a shared SQLite connection with WAL mode enabled."""
    global _conn
    if _conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.row_factory = sqlite3.Row
        logger.info("SQLite connection opened: %s (WAL mode)", DB_PATH)
    return _conn


def init_db() -> None:
    conn = get_connection()
    with _write_lock:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Add source_url column if upgrading from old schema
        try:
            conn.execute("ALTER TABLE companies ADD COLUMN source_url TEXT")
            logger.info("Added source_url column to companies table")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.commit()
    seed_if_empty()


def seed_if_empty() -> None:
    if not SEED_PATH.exists():
        return
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM companies").fetchone()["c"]
    if count:
        return
    records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    with _write_lock:
        for record in records:
            source_url = _extract_source_url(record)
            conn.execute(
                "INSERT INTO companies (source_url, data) VALUES (?, ?)",
                (source_url, json.dumps(record)),
            )
        conn.commit()
    logger.info("Seeded %d companies from %s", len(records), SEED_PATH.name)


def save_company(profile: dict[str, Any]) -> None:
    """Save an enriched profile, skipping if the same URL was enriched within 24 hours."""
    conn = get_connection()
    source_url = _extract_source_url(profile)

    # Duplicate detection: skip if enriched within the last 24 hours
    if source_url:
        existing = conn.execute(
            """
            SELECT id FROM companies
            WHERE source_url = ?
              AND created_at > datetime('now', '-24 hours')
            LIMIT 1
            """,
            (source_url,),
        ).fetchone()
        if existing:
            logger.info(
                "Skipping duplicate — URL %s was enriched within the last 24h",
                source_url,
            )
            return

    with _write_lock:
        conn.execute(
            "INSERT INTO companies (source_url, data) VALUES (?, ?)",
            (source_url, json.dumps(profile)),
        )
        conn.commit()
    logger.info("Saved enrichment for: %s", source_url or "(unknown URL)")


def list_companies(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Return enriched companies with pagination (newest first)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT data FROM companies ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        try:
            records.append(json.loads(row["data"]))
        except json.JSONDecodeError:
            continue
    return records


def _extract_source_url(profile: dict[str, Any]) -> str:
    """Best-effort extraction of the canonical URL from a profile dict."""
    return str(profile.get("source_url", "") or "").strip().rstrip("/").lower()
