from datetime import date, datetime, timedelta, timezone

from digest import fetch, render, store

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
SINCE = NOW - timedelta(days=7)
SOURCE = fetch.Source(name="Example", url="https://example.com/feed.xml")

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Example</title>
  <item><title>Fresh post</title><link>https://example.com/fresh</link>
        <guid>fresh-1</guid><pubDate>Fri, 25 Sep 2026 08:00:00 GMT</pubDate></item>
  <item><title>Old post</title><link>https://example.com/old</link>
        <guid>old-1</guid><pubDate>Mon, 01 Sep 2026 08:00:00 GMT</pubDate></item>
  <item><title>Undated [draft]</title><link>https://example.com/undated</link></item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title>
  <entry><title>Atom entry</title><id>urn:atom:1</id>
         <link href="https://example.org/a"/><updated>2026-09-26T10:00:00Z</updated></entry>
</feed>"""


def test_parse_filters_by_date_and_stamps_undated():
    items = fetch.parse_items(SOURCE, RSS, SINCE, NOW)
    titles = {i.title: i for i in items}
    assert set(titles) == {"Fresh post", "Undated [draft]"}
    assert titles["Undated [draft]"].published == NOW


def test_parse_atom():
    atom = fetch.Source(name="Atom", url="https://example.org/atom")
    [item] = fetch.parse_items(atom, ATOM, SINCE, NOW)
    assert item.link == "https://example.org/a"
    assert item.published == datetime(2026, 9, 26, 10, tzinfo=timezone.utc)


def test_store_dedupes(tmp_path):
    conn = store.connect(tmp_path / "db.sqlite")
    items = fetch.parse_items(SOURCE, RSS, SINCE, NOW)
    assert store.save_items(conn, items) == 2
    assert store.save_items(conn, items) == 0
    assert len(store.items_since(conn, SINCE)) == 2


def test_render_groups_by_source(tmp_path):
    items = fetch.parse_items(SOURCE, RSS, SINCE, NOW)
    items += fetch.parse_items(fetch.Source("Atom", "u"), ATOM, SINCE, NOW)
    path = render.write_digest(items, tmp_path, date(2026, 9, 27), 7)
    text = path.read_text()
    assert path.name == "digest-2026-09-27.md"
    assert text.index("## Atom") < text.index("## Example")
    assert r"[Undated \[draft\]](https://example.com/undated)" in text


def test_load_sources(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("feeds:\n  - name: A\n    url: https://a/feed\n  - url: https://b/feed\n")
    assert fetch.load_sources(p) == [
        fetch.Source("A", "https://a/feed"),
        fetch.Source("https://b/feed", "https://b/feed"),
    ]
