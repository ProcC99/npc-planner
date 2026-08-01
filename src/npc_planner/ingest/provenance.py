import hashlib
import json
import sqlite3
from typing import Any


def _hash_value(value: Any) -> str:
    """Compute sha256 hash string for value."""
    if isinstance(value, (dict, list)):
        payload = json.dumps(value, sort_keys=True)
    else:
        payload = str(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_field(
    conn: sqlite3.Connection,
    entity_type: str,
    entity_key: str,
    field_path: str,
    source_type: str,
    value: Any,
    confidence: float = 1.0,
    source_file: str | None = None,
) -> int:
    """Record a single field provenance entry in the provenance table. Returns provenance_id."""
    val_hash = _hash_value(value)
    cursor = conn.execute(
        """
        INSERT INTO provenance (
            entity_type, entity_key, field_path, source_type,
            source_file, value_hash, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_type,
            entity_key,
            field_path,
            source_type,
            source_file,
            val_hash,
            float(confidence),
        ),
    )
    conn.commit()
    prov_id = cursor.lastrowid
    assert prov_id is not None
    return int(prov_id)


def entity_confidence(
    conn: sqlite3.Connection, entity_type: str, entity_key: str
) -> float:
    """Calculate the minimum confidence across recorded fields for an entity."""
    row = conn.execute(
        "SELECT MIN(confidence) FROM provenance WHERE entity_type = ? AND entity_key = ?",
        (entity_type, entity_key),
    ).fetchone()

    if row is None or row[0] is None:
        return 1.0
    return float(row[0])


def uncertainties(
    conn: sqlite3.Connection, min_confidence: float = 0.5
) -> list[dict[str, Any]]:
    """Query provenance records with confidence strictly below min_confidence."""
    cursor = conn.execute(
        """
        SELECT provenance_id, entity_type, entity_key, field_path, source_type,
               source_file, value_hash, confidence, verification_status
        FROM provenance
        WHERE confidence < ?
        ORDER BY confidence ASC
        """,
        (float(min_confidence),),
    )
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
