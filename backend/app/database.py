import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DATABASE_URL


def _database_path() -> str:
    # Supports the assignment's sqlite:////data/app.db and local sqlite:///./app.db formats.
    if DATABASE_URL.startswith("sqlite:////"):
        return "/" + DATABASE_URL[len("sqlite:////"):]
    if DATABASE_URL.startswith("sqlite:///"):
        return DATABASE_URL[len("sqlite:///"):]
    raise ValueError("DATABASE_URL must use SQLite, for example sqlite:////data/app.db")


DB_PATH = _database_path()


def initialize_database() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id)")
        connection.commit()


@contextmanager
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def database_is_ready() -> bool:
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False
