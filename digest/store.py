"""SQLite persistence and deduplication of feed items."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from digest.fetch import Item

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id         TEXT PRIMARY KEY,
    source     TEXT NOT NULL,
    title      TEXT NOT NULL,
    link       TEXT NOT NULL,
    summary    TEXT NOT NULL,
    published  TEXT NOT NULL,  -- ISO 8601, UTC
    first_seen TEXT NOT NULL   -- ISO 8601, UTC
);
CREATE INDEX IF NOT EXISTS idx_items_published ON items (published);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    if path.parent != Path(""):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_items(conn: sqlite3.Connection, items: list[Item]) -> int:
    """Insert items, ignoring ones already stored. Returns the number of new rows."""
    now = _iso(datetime.now(timezone.utc))
    before = conn.total_changes
    with conn:
        conn.executemany(
            "INSERT OR IGNORE INTO items (id, source, title, link, summary, published, first_seen)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (i.id, i.source, i.title, i.link, i.summary, _iso(i.published), now)
                for i in items
            ],
        )
    return conn.total_changes - before


def items_since(conn: sqlite3.Connection, since: datetime) -> list[Item]:
    """All stored items published at or after `since`, newest first."""
    rows = conn.execute(
        "SELECT * FROM items WHERE published >= ? ORDER BY published DESC, title",
        (_iso(since),),
    ).fetchall()
    return [
        Item(
            id=r["id"],
            source=r["source"],
            title=r["title"],
            link=r["link"],
            summary=r["summary"],
            published=datetime.fromisoformat(r["published"]),
        )
        for r in rows
    ]


def _iso(dt: datetime) -> str:
    # Fixed-width UTC format so string comparison in SQL matches time order.
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
