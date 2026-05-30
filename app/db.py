from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "companies.db"
SEED_PATH = DATA_DIR / "seed_companies.json"


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    seed_if_empty()


def seed_if_empty() -> None:
    if not SEED_PATH.exists():
        return
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM companies").fetchone()["c"]
        if count:
            return
        records = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        for record in records:
            conn.execute("INSERT INTO companies (data) VALUES (?)", (json.dumps(record),))
        conn.commit()


def save_company(profile: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO companies (data) VALUES (?)", (json.dumps(profile),))
        conn.commit()


def list_companies() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT data FROM companies ORDER BY created_at DESC, id DESC").fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        try:
            records.append(json.loads(row["data"]))
        except json.JSONDecodeError:
            continue
    return records
