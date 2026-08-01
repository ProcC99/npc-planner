from pathlib import Path

from npc_planner.db.session import create_connection, get_db, init_db


def test_create_connection_pragmas() -> None:
    conn = create_connection(":memory:")
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1
    conn.close()


def test_init_db() -> None:
    conn = create_connection(":memory:")
    init_db(conn)
    tables_count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    views_count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='view'"
    ).fetchone()[0]
    assert tables_count == 31
    assert views_count == 2
    conn.close()


def test_get_db_context_manager(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    with get_db(db_file) as conn:
        init_db(conn)
        tables_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert tables_count == 31
    assert db_file.exists()
