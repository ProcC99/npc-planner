from pathlib import Path

import pytest

from npc_planner.db.session import create_connection, init_db
from npc_planner.ingest.baseline import load_baseline_dumps


def test_load_baseline_dumps_m1_tiny() -> None:
    conn = create_connection(":memory:")
    init_db(conn)

    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    counts = load_baseline_dumps(conn, fixture_dir)
    assert isinstance(counts, dict)
    assert counts["stg_species"] == 10
    assert counts["stg_forms"] == 10
    assert counts["stg_moves"] == 10
    assert counts["stg_abilities"] == 10
    assert counts["stg_type_matchups"] == 10

    build_info = conn.execute("SELECT build_id FROM build_info").fetchone()
    assert build_info is not None
    assert build_info[0] == "m1_tiny_fixture_v1"
    conn.close()


def test_load_baseline_dumps_idempotency() -> None:
    conn = create_connection(":memory:")
    init_db(conn)

    fixture_dir = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "m1_tiny"
    counts1 = load_baseline_dumps(conn, fixture_dir)
    counts2 = load_baseline_dumps(conn, fixture_dir)

    assert counts1 == counts2
    total_forms = conn.execute("SELECT COUNT(*) FROM stg_forms").fetchone()[0]
    assert total_forms == 10
    conn.close()


def test_load_baseline_dumps_missing_directory(tmp_path: Path) -> None:
    conn = create_connection(":memory:")
    init_db(conn)
    missing_dir = tmp_path / "non_existent"
    with pytest.raises(FileNotFoundError):
        load_baseline_dumps(conn, missing_dir)
    conn.close()
