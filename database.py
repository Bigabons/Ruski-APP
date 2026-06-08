import os
import sqlite3
from pathlib import Path

# DATA_DIR lets Coolify/Docker mount a persistent volume (e.g. /data)
_data_dir = Path(os.getenv("DATA_DIR", str(Path(__file__).parent)))
DB_PATH = _data_dir / "rosyjski.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id   INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                pin_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS words (
                id        INTEGER PRIMARY KEY,
                ru        TEXT NOT NULL,
                translit  TEXT NOT NULL,
                pl        TEXT NOT NULL,
                kategoria TEXT NOT NULL,
                typ       TEXT NOT NULL DEFAULT 'slowo'
            );

            CREATE TABLE IF NOT EXISTS progress (
                id           INTEGER PRIMARY KEY,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                word_id      INTEGER NOT NULL REFERENCES words(id),
                repetitions  INTEGER NOT NULL DEFAULT 0,
                interval_days REAL NOT NULL DEFAULT 1.0,
                ease         REAL NOT NULL DEFAULT 2.5,
                due_date     TEXT NOT NULL,
                last_seen    TEXT,
                UNIQUE(user_id, word_id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                expires_at TEXT NOT NULL
            );
        """)
    conn.close()
