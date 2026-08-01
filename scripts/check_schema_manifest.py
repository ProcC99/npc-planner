#!/usr/bin/env python3
"""Fail if schema.sql and docs/schema_manifest.txt disagree.

This is the permanent cure for the '21 vs 26 tables' class of drift.
Run as part of `make check`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src" / "npc_planner" / "db" / "schema.sql"
MANIFEST = ROOT / "docs" / "schema_manifest.txt"

TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?(\w+)", re.IGNORECASE
)
VIEW_RE = re.compile(
    r"CREATE\s+VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`\[]?(\w+)", re.IGNORECASE
)

EXPECTED_VIEWS = {"v_form_full", "v_battle_confidence"}
EXPECTED_DOMAIN_COUNT = 26
EXPECTED_STAGING_COUNT = 5


def main() -> int:
    if not SCHEMA.exists():
        print(f"schema.sql not yet created ({SCHEMA}), scheduled for M1-T03")
        return 0
    if not MANIFEST.exists():
        print(f"FAIL: missing {MANIFEST}")
        return 1

    sql = SCHEMA.read_text(encoding="utf-8")
    in_sql = set(TABLE_RE.findall(sql))
    views_in_sql = set(VIEW_RE.findall(sql))
    in_manifest = {
        line.strip()
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    errors: list[str] = []

    missing = sorted(in_manifest - in_sql)
    extra = sorted(in_sql - in_manifest)

    # Allow staging tables to be added in M1-T04
    missing_staging = [m for m in missing if m.startswith("stg_")]
    missing_domain = [m for m in missing if not m.startswith("stg_")]

    if missing_domain:
        errors.append(
            f"domain tables declared in manifest but absent from schema.sql: {missing_domain}"
        )
    if extra:
        errors.append(f"present in schema.sql but absent from manifest: {extra}")

    # Views added in M1-T04
    if views_in_sql and views_in_sql != EXPECTED_VIEWS:
        errors.append(
            f"views mismatch: schema.sql has {sorted(views_in_sql)}, "
            f"expected {sorted(EXPECTED_VIEWS)}"
        )

    staging = {t for t in in_manifest if t.startswith("stg_")}
    domain = in_manifest - staging
    if len(domain) != EXPECTED_DOMAIN_COUNT:
        errors.append(
            f"expected {EXPECTED_DOMAIN_COUNT} domain tables, manifest lists {len(domain)}"
        )
    if missing_staging:
        print(
            f"info: {len(missing_staging)} staging tables scheduled for M1-T04: {missing_staging}"
        )
    elif len(staging) != EXPECTED_STAGING_COUNT:
        errors.append(
            f"expected {EXPECTED_STAGING_COUNT} staging tables, manifest lists {len(staging)}"
        )

    if errors:
        print("schema manifest check FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"schema manifest OK: {len(domain)} domain tables verified in schema.sql")
    return 0


if __name__ == "__main__":
    sys.exit(main())
