import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from npc_planner.db.session import get_db, init_db
from npc_planner.ingest.baseline import load_baseline_dumps


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def build_database(
    raw_dir: Path | str,
    db_out: Path | str,
    lock_out: Path | str | None = None,
) -> Path:
    """Build pure SQLite planner.db from raw baseline dumps and generate lock.json. Returns db path."""
    raw_path = Path(raw_dir).resolve()
    db_path = Path(db_out).resolve()

    if db_path.exists():
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db(db_path) as conn:
        init_db(conn)
        counts = load_baseline_dumps(conn, raw_path)

    sha256_hash = _compute_sha256(db_path)

    lock_file = (
        Path(lock_out).resolve()
        if lock_out
        else db_path.parent / f"{db_path.name}.lock.json"
    )

    lock_data = {
        "build_id": f"build_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "built_at": datetime.now(UTC).isoformat(),
        "db_path": str(db_path),
        "sha256": sha256_hash,
        "counts": counts,
    }
    lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

    return db_path
