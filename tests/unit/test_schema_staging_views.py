import sqlite3
from pathlib import Path


def test_schema_staging_and_views() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "db"
        / "schema.sql"
    )
    conn = sqlite3.connect(":memory:")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)

    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    views = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
    ]

    assert len(tables) == 31
    assert "stg_species" in tables
    assert "stg_forms" in tables
    assert "stg_moves" in tables
    assert "stg_abilities" in tables
    assert "stg_type_matchups" in tables

    assert "v_form_full" in views
    assert "v_battle_confidence" in views


def test_views_queryable() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "npc_planner"
        / "db"
        / "schema.sql"
    )
    conn = sqlite3.connect(":memory:")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)

    res_forms = conn.execute("SELECT * FROM v_form_full LIMIT 1").fetchall()
    res_conf = conn.execute("SELECT * FROM v_battle_confidence LIMIT 1").fetchall()
    assert res_forms == []
    assert res_conf == []
