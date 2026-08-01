#!/usr/bin/env python3
"""Fetch or populate baseline raw data dumps into data/raw/ directory.

Supports offline fixture mode via `--fixture m1_tiny`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "gen3_official"


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch baseline raw data dumps into target directory."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Target output directory for raw JSON dumps.",
    )
    parser.add_argument(
        "--fixture",
        "-f",
        type=str,
        default=None,
        help="Use pre-authored offline test fixture (e.g. 'm1_tiny').",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files in target directory.",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    opts = parse_args(args)
    output_dir: Path = opts.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if opts.fixture:
        fixture_path = FIXTURES_DIR / opts.fixture
        if not fixture_path.exists():
            print(f"Error: fixture '{opts.fixture}' not found at {fixture_path}")
            return 1

        json_files = list(fixture_path.glob("*.json"))
        if not json_files:
            print(f"Error: no JSON files found in fixture {fixture_path}")
            return 1

        for src in json_files:
            dst = output_dir / src.name
            if dst.exists() and not opts.force:
                print(f"Skipping {dst.name} (already exists, use --force to overwrite)")
                continue
            shutil.copy2(src, dst)
            print(f"Copied {src.name} -> {dst}")

        print(f"Successfully populated {output_dir} from fixture '{opts.fixture}'")
        return 0

    # Non-fixture / production fetch fallback (offline placeholder)
    meta_path = output_dir / "meta.json"
    if meta_path.exists() and not opts.force:
        print(f"Baseline raw dumps already exist at {output_dir}")
        return 0

    dummy_meta = {
        "build_id": "gen3_official_v1",
        "built_at": "2026-08-01T00:00:00Z",
        "tool_version": "0.1.0a1",
        "baseline_version": "gen3_official",
        "hack_name": "Vanilla Gen 3",
        "hack_version": "1.0",
        "engine": "pokeemerald",
        "source_manifest": "{}",
    }
    meta_path.write_text(json.dumps(dummy_meta, indent=2), encoding="utf-8")
    print(f"Created baseline metadata in {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
