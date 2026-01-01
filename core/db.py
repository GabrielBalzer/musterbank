"""SQLite access and schema migrations for the core bank."""
import os
import sqlite3
from datetime import datetime, timezone

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
BUSY_TIMEOUT_SECONDS = 30


def connect(path):
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_SECONDS, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _list_migrations():
    files = [name for name in os.listdir(MIGRATIONS_DIR) if name.endswith(".sql")]
    return sorted(files)


def current_version(conn):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
    ).fetchone()
    if row is None:
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def migrate(conn):
    """Apply all migrations newer than the database version. Returns the new version."""
    version = current_version(conn)
    for name in _list_migrations():
        number = int(name.split("_", 1)[0])
        if number <= version:
            continue
        with open(os.path.join(MIGRATIONS_DIR, name), encoding="utf-8") as fh:
            script = fh.read()
        applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.executescript(
            "BEGIN;\n%s\nINSERT INTO schema_version (version, applied_at) VALUES (%d, '%s');\nCOMMIT;"
            % (script, number, applied_at)
        )
        version = number
    return version
