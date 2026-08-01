import json
import sqlite3
from pathlib import Path

from npc_planner.ingest.build import build_database


def test_build_database_m1_tiny(tmp_path: Path) -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    db_file = tmp_path / "planner.db"
    lock_file = tmp_path / "planner.db.lock.json"

    res_db = build_database(fixture_dir, db_file, lock_file)
    assert res_db == db_file
    assert db_file.exists()
    assert lock_file.exists()

    lock_data = json.loads(lock_file.read_text(encoding="utf-8"))
    assert "build_id" in lock_data
    assert "sha256" in lock_data
    assert "counts" in lock_data
    assert lock_data["counts"]["stg_forms"] == 10

    # Verify tables created and staging loaded into SQLite
    conn = sqlite3.connect(db_file)
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    assert len(tables) == 31
    stg_forms = conn.execute("SELECT COUNT(*) FROM stg_forms").fetchone()[0]
    assert stg_forms == 10
    conn.close()


def test_build_database_reproducibility(tmp_path: Path) -> None:
    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    db1 = tmp_path / "db1.db"
    lock1 = tmp_path / "lock1.json"
    db2 = tmp_path / "db2.db"
    lock2 = tmp_path / "lock2.json"

    build_database(fixture_dir, db1, lock1)
    build_database(fixture_dir, db2, lock2)

    data1 = json.loads(lock1.read_text(encoding="utf-8"))
    data2 = json.loads(lock2.read_text(encoding="utf-8"))
    assert data1["counts"] == data2["counts"]
