import sqlite3
from pathlib import Path


def test_schema_ddl_execution() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "db"
        / "schema.sql"
    )
    assert schema_path.exists()
    conn = sqlite3.connect(":memory:")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    assert len(tables) == 31
    assert "build_info" in tables
    assert "provenance" in tables
    assert "species" in tables
    assert "forms" in tables
    assert "abilities" in tables
    assert "moves" in tables
    assert "learnsets" in tables
    assert "trainer_specs" in tables
    assert "generated_teams" in tables
    assert "stg_species" in tables


def test_schema_ddl_pragmas() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "db"
        / "schema.sql"
    )
    sql = schema_path.read_text(encoding="utf-8")
    assert "PRAGMA foreign_keys = ON;" in sql
    assert "PRAGMA journal_mode = WAL;" in sql
