"""Load feed sources and fetch recent items from them."""

from __future__ import annotations

import calendar
import hashlib
import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml

log = logging.getLogger(__name__)

USER_AGENT = "rss-digest/0.1 (+https://github.com/md0092651/android-agent-skills)"
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Source:
    name: str
    url: str


@dataclass(frozen=True)
class Item:
    id: str
    source: str
    title: str
    link: str
    summary: str
    published: datetime  # always timezone-aware UTC


def load_sources(path: str | Path) -> list[Source]:
    """Read sources.yaml. Expected shape:

    feeds:
      - name: Example Blog
        url: https://example.com/feed.xml
    """
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    feeds = data.get("feeds") or []
    sources = []
    for i, entry in enumerate(feeds):
        if not isinstance(entry, dict) or not entry.get("url"):
            raise ValueError(f"{path}: feeds[{i}] must be a mapping with a 'url'")
        sources.append(Source(name=entry.get("name") or entry["url"], url=entry["url"]))
    return sources


def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return resp.read()


def parse_items(source: Source, content: bytes | str, since: datetime, now: datetime) -> list[Item]:
    """Parse raw feed content and return items published at or after `since`.

    Entries with no date are stamped with `now`; the store keeps the first
    time an item was seen, so they won't be re-dated on later runs.
    """
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"could not parse feed: {parsed.bozo_exception}")

    items = []
    for entry in parsed.entries:
        published = _entry_datetime(entry) or now
        if published < since:
            continue
        link = entry.get("link", "")
        title = (entry.get("title") or link or "(untitled)").strip()
        items.append(
            Item(
                id=_entry_id(entry, source),
                source=source.name,
                title=title,
                link=link,
                summary=(entry.get("summary") or "").strip(),
                published=published,
            )
        )
    return items


def fetch_source(source: Source, since: datetime, now: datetime | None = None) -> list[Item]:
    now = now or datetime.now(timezone.utc)
    return parse_items(source, download(source.url), since, now)


def fetch_all(sources: list[Source], since: datetime) -> list[Item]:
    """Fetch every source; a failing feed is logged and skipped."""
    now = datetime.now(timezone.utc)
    items: list[Item] = []
    for source in sources:
        try:
            got = fetch_source(source, since, now)
        except Exception as exc:  # network, HTTP, or parse errors
            log.warning("skipping %s (%s): %s", source.name, source.url, exc)
            continue
        log.info("%s: %d recent item(s)", source.name, len(got))
        items.extend(got)
    return items


def _entry_datetime(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        struct = entry.get(key)
        if struct:
            # feedparser normalizes these to UTC struct_time
            return datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
    return None


def _entry_id(entry, source: Source) -> str:
    """Stable dedupe key: the entry's guid/id, else its link, else source+title."""
    key = entry.get("id") or entry.get("link") or f"{source.url}|{entry.get('title', '')}"
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()
