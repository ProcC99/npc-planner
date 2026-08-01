import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


def create_connection(db_path: Path | str = ":memory:") -> sqlite3.Connection:
    """Connect to SQLite database, configure WAL mode and enable foreign keys."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    if str(db_path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Execute schema.sql to initialize database tables and views."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)


@contextmanager
def get_db(
    db_path: Path | str = ":memory:",
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing a managed database connection."""
    conn = create_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
