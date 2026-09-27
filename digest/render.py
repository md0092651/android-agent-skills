"""Render stored items as a markdown digest grouped by source."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from digest.fetch import Item


def render_markdown(items: list[Item], day: date, days: int) -> str:
    lines = [f"# Feed digest — {day.isoformat()}", ""]
    if not items:
        lines.append(f"_No items in the last {days} days._")
        return "\n".join(lines) + "\n"

    by_source: dict[str, list[Item]] = defaultdict(list)
    for item in items:
        by_source[item.source].append(item)

    lines.append(f"{len(items)} item(s) from {len(by_source)} source(s) in the last {days} days.")
    for source in sorted(by_source, key=str.casefold):
        lines += ["", f"## {source}", ""]
        for item in sorted(by_source[source], key=lambda i: i.published, reverse=True):
            title = _escape(item.title)
            entry = f"[{title}]({item.link})" if item.link else title
            lines.append(f"- {entry} — {item.published:%Y-%m-%d}")
    return "\n".join(lines) + "\n"


def write_digest(items: list[Item], out_dir: str | Path, day: date, days: int) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"digest-{day.isoformat()}.md"
    path.write_text(render_markdown(items, day, days), encoding="utf-8")
    return path


def _escape(text: str) -> str:
    """Keep titles on one line and stop brackets from breaking link syntax."""
    text = " ".join(text.split())
    return text.replace("[", r"\[").replace("]", r"\]")
