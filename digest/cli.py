"""Command-line entry point: fetch -> store -> render."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from digest import fetch, render, store


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="digest",
        description="Fetch RSS/Atom feeds and write a markdown digest of recent items.",
    )
    p.add_argument("--sources", default="sources.yaml", help="feed list (default: %(default)s)")
    p.add_argument("--db", default="digest.db", help="SQLite database (default: %(default)s)")
    p.add_argument("--out-dir", default="output", help="digest directory (default: %(default)s)")
    p.add_argument("--days", type=int, default=7, help="look-back window (default: %(default)s)")
    p.add_argument("-v", "--verbose", action="store_true", help="log each feed")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=args.days)

    sources = fetch.load_sources(args.sources)
    if not sources:
        print(f"No feeds listed in {args.sources}")
        return 1

    items = fetch.fetch_all(sources, since)
    conn = store.connect(args.db)
    try:
        new = store.save_items(conn, items)
        recent = store.items_since(conn, since)
    finally:
        conn.close()

    path = render.write_digest(recent, args.out_dir, now.date(), args.days)
    print(f"{new} new item(s) stored; {len(recent)} in digest -> {path}")
    return 0
