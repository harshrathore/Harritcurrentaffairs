import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config


def get_connection() -> sqlite3.Connection:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS releases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prid INTEGER UNIQUE NOT NULL,
        title TEXT,
        publication_date TEXT,
        publication_time TEXT,
        ministry TEXT,
        department TEXT,
        location TEXT,
        language TEXT DEFAULT 'English',
        region TEXT DEFAULT 'National',
        canonical_url TEXT,
        successful_url TEXT,
        page_variant TEXT,
        full_text TEXT,
        content_hash TEXT,
        first_seen_at TEXT,
        last_updated_at TEXT,
        status TEXT DEFAULT 'pending'
    );

    CREATE TABLE IF NOT EXISTS discovery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prid INTEGER NOT NULL,
        method TEXT NOT NULL,
        source_url TEXT,
        parent_prid INTEGER,
        discovered_at TEXT,
        FOREIGN KEY (prid) REFERENCES releases(prid)
    );

    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prid INTEGER NOT NULL,
        url TEXT,
        filename TEXT,
        file_type TEXT,
        mime_type TEXT,
        local_path TEXT,
        sha256 TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (prid) REFERENCES releases(prid)
    );

    CREATE TABLE IF NOT EXISTS http_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        prid INTEGER,
        status_code INTEGER,
        attempt INTEGER DEFAULT 1,
        error TEXT,
        requested_at TEXT,
        response_time REAL
    );

    CREATE TABLE IF NOT EXISTS crawl_dates (
        date TEXT NOT NULL,
        method TEXT NOT NULL,
        discovered_count INTEGER DEFAULT 0,
        validated_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        last_attempt TEXT,
        error TEXT,
        PRIMARY KEY (date, method)
    );

    CREATE TABLE IF NOT EXISTS crawl_ministries (
        date TEXT NOT NULL,
        ministry TEXT NOT NULL,
        discovered_count INTEGER DEFAULT 0,
        validated_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        PRIMARY KEY (date, ministry)
    );

    CREATE INDEX IF NOT EXISTS idx_releases_date ON releases(publication_date);
    CREATE INDEX IF NOT EXISTS idx_releases_status ON releases(status);
    CREATE INDEX IF NOT EXISTS idx_discovery_prid ON discovery(prid);
    CREATE INDEX IF NOT EXISTS idx_discovery_method ON discovery(method);
    """)
    conn.commit()
    conn.close()


def content_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def upsert_release(prid: int, **kwargs) -> bool:
    conn = get_connection()
    now = datetime.now().isoformat()
    existing = conn.execute(
        "SELECT prid, content_hash FROM releases WHERE prid=?", (prid,)
    ).fetchone()

    if existing:
        new_hash = content_hash(kwargs.get("full_text", ""))
        if existing["content_hash"] == new_hash:
            conn.close()
            return False
        sets = []
        vals = []
        for k, v in kwargs.items():
            if v is not None:
                sets.append(f"{k}=?")
                vals.append(v)
        sets.append("last_updated_at=?")
        vals.append(now)
        vals.append(prid)
        conn.execute(
            f"UPDATE releases SET {', '.join(sets)} WHERE prid=?", vals
        )
    else:
        cols = ["prid", "first_seen_at", "last_updated_at", "content_hash"]
        vals_list = [prid, now, now, content_hash(kwargs.get("full_text", ""))]
        for k, v in kwargs.items():
            if v is not None:
                cols.append(k)
                vals_list.append(v)
        placeholders = ",".join(["?"] * len(cols))
        conn.execute(
            f"INSERT INTO releases ({','.join(cols)}) VALUES ({placeholders})",
            vals_list,
        )
    conn.commit()
    conn.close()
    return True


def add_discovery(prid: int, method: str, source_url: str = "", parent_prid: int = None):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO discovery (prid, method, source_url, parent_prid, discovered_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (prid, method, source_url, parent_prid, now),
    )
    conn.commit()
    conn.close()


def get_pending_releases(limit: int = 500) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT prid FROM releases WHERE status='pending' ORDER BY prid LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [r["prid"] for r in rows]


def get_release(prid: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM releases WHERE prid=?", (prid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_prids() -> set:
    conn = get_connection()
    rows = conn.execute("SELECT prid FROM releases").fetchall()
    conn.close()
    return {r["prid"] for r in rows}


def get_valid_prids() -> set:
    conn = get_connection()
    rows = conn.execute("SELECT prid FROM releases WHERE status='valid'").fetchall()
    conn.close()
    return {r["prid"] for r in rows}


def count_by_status() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM releases GROUP BY status"
    ).fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}


def count_by_date() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT publication_date, COUNT(*) as cnt FROM releases "
        "WHERE status='valid' GROUP BY publication_date ORDER BY publication_date"
    ).fetchall()
    conn.close()
    return {r["publication_date"]: r["cnt"] for r in rows}


def update_crawl_date(date_str: str, method: str, discovered: int, validated: int, status: str, error: str = None):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO crawl_dates (date, method, discovered_count, validated_count, status, last_attempt, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (date_str, method, discovered, validated, status, now, error),
    )
    conn.commit()
    conn.close()


def get_crawl_dates(method: str) -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT date, discovered_count, validated_count, status FROM crawl_dates WHERE method=?",
        (method,),
    ).fetchall()
    conn.close()
    return {r["date"]: dict(r) for r in rows}


def get_discovery_methods(prid: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT method FROM discovery WHERE prid=?", (prid,)
    ).fetchall()
    conn.close()
    return [r["method"] for r in rows]


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM releases").fetchone()["c"]
    valid = conn.execute("SELECT COUNT(*) as c FROM releases WHERE status='valid'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM releases WHERE status='pending'").fetchone()["c"]
    failed = conn.execute("SELECT COUNT(*) as c FROM releases WHERE status='failed'").fetchone()["c"]
    conn.close()
    return {"total": total, "valid": valid, "pending": pending, "failed": failed}
