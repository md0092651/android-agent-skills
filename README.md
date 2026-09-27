# rss-digest

A small command-line tool that reads a list of RSS/Atom feeds, fetches items
from the last 7 days, dedupes them into a SQLite database, and writes a
markdown digest grouped by source.

```
sources.yaml ──fetch──▶ items ──store──▶ digest.db ──render──▶ output/digest-YYYY-MM-DD.md
```

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configure feeds

Edit `sources.yaml`:

```yaml
feeds:
  - name: Python Insider                      # section heading in the digest
    url: https://pythoninsider.blogspot.com/feeds/posts/default
  - url: https://hnrss.org/frontpage          # name defaults to the URL
```

## Run

```bash
python -m digest
# 12 new item(s) stored; 34 in digest -> output/digest-2026-09-27.md
```

Options:

| Flag          | Default        | Meaning                                  |
|---------------|----------------|------------------------------------------|
| `--sources`   | `sources.yaml` | Feed list                                |
| `--db`        | `digest.db`    | SQLite database file                     |
| `--out-dir`   | `output`       | Where digests are written                |
| `--days`      | `7`            | Look-back window in days                 |
| `-v`          | off            | Log how many items each feed returned    |

Running it more than once a day overwrites that day's digest. To run it
automatically, add a cron entry such as:

```
0 7 * * * cd /path/to/repo && .venv/bin/python -m digest
```

## How it works

| Module             | Concern                                                                 |
|--------------------|-------------------------------------------------------------------------|
| `digest/fetch.py`  | Loads `sources.yaml`, downloads each feed, parses it with `feedparser`, keeps items newer than the window. |
| `digest/store.py`  | SQLite `items` table. The primary key is a hash of the entry's guid/id (falling back to its link), so re-runs insert only new items. |
| `digest/render.py` | Reads the window back from the database and writes the markdown file, one `##` section per source, newest first. |
| `digest/cli.py`    | Wires the three together with `argparse`.                               |

Notes:

- The digest is built from the database, not just the current fetch, so an
  item still appears if its feed was down on a later run.
- A feed that fails to download or parse is logged and skipped; the rest of
  the run continues.
- Entries without any date are stamped with the time they were first seen.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
