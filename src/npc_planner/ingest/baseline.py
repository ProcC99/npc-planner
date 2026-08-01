import json
import sqlite3
from pathlib import Path
from typing import Any


def load_baseline_dumps(conn: sqlite3.Connection, raw_dir: Path | str) -> int:
    """Load raw JSON files from raw_dir into stg_* tables and build_info.

    Returns the total number of staging records inserted (including build_info).
    """
    path = Path(raw_dir).resolve()
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Raw dump directory not found: {raw_dir}")

    meta_file = path / "meta.json"
    if not meta_file.exists():
        raise FileNotFoundError(f"Missing meta.json in {raw_dir}")

    meta_data: dict[str, Any] = json.loads(meta_file.read_text(encoding="utf-8"))
    conn.execute(
        """
        INSERT OR REPLACE INTO build_info (
            build_id, built_at, tool_version, baseline_version,
            hack_name, hack_version, engine, source_manifest
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            meta_data.get("build_id"),
            meta_data.get("built_at"),
            meta_data.get("tool_version"),
            meta_data.get("baseline_version"),
            meta_data.get("hack_name"),
            meta_data.get("hack_version"),
            meta_data.get("engine"),
            meta_data.get("source_manifest", "{}"),
        ),
    )
    inserted_count = 1

    # Ingest species
    species_file = path / "species.json"
    if species_file.exists():
        species_list: list[dict[str, Any]] = json.loads(
            species_file.read_text(encoding="utf-8")
        )
        for item in species_list:
            conn.execute(
                "INSERT OR REPLACE INTO stg_species (species_slug, species_name, raw_payload) VALUES (?, ?, ?)",
                (
                    item["species_slug"],
                    item["species_name"],
                    json.dumps(item),
                ),
            )
            inserted_count += 1

    # Ingest forms
    forms_file = path / "forms.json"
    if forms_file.exists():
        forms_list: list[dict[str, Any]] = json.loads(
            forms_file.read_text(encoding="utf-8")
        )
        for item in forms_list:
            conn.execute(
                "INSERT OR REPLACE INTO stg_forms (form_id, species_slug, raw_payload) VALUES (?, ?, ?)",
                (
                    item["form_id"],
                    item["species_slug"],
                    json.dumps(item),
                ),
            )
            inserted_count += 1

    # Ingest moves
    moves_file = path / "moves.json"
    if moves_file.exists():
        moves_list: list[dict[str, Any]] = json.loads(
            moves_file.read_text(encoding="utf-8")
        )
        for item in moves_list:
            conn.execute(
                "INSERT OR REPLACE INTO stg_moves (move_slug, move_name, raw_payload) VALUES (?, ?, ?)",
                (
                    item["move_slug"],
                    item["move_name"],
                    json.dumps(item),
                ),
            )
            inserted_count += 1

    # Ingest abilities
    abilities_file = path / "abilities.json"
    if abilities_file.exists():
        abilities_list: list[dict[str, Any]] = json.loads(
            abilities_file.read_text(encoding="utf-8")
        )
        for item in abilities_list:
            conn.execute(
                "INSERT OR REPLACE INTO stg_abilities (ability_slug, ability_name, raw_payload) VALUES (?, ?, ?)",
                (
                    item["ability_slug"],
                    item["ability_name"],
                    json.dumps(item),
                ),
            )
            inserted_count += 1

    # Ingest type_matchups
    matchups_file = path / "type_matchups.json"
    if matchups_file.exists():
        matchups_list: list[dict[str, Any]] = json.loads(
            matchups_file.read_text(encoding="utf-8")
        )
        for item in matchups_list:
            conn.execute(
                "INSERT OR REPLACE INTO stg_type_matchups (attacking_type, defending_type, multiplier) VALUES (?, ?, ?)",
                (
                    item["attacking_type"],
                    item["defending_type"],
                    item["multiplier"],
                ),
            )
            inserted_count += 1

    conn.commit()
    return inserted_count
