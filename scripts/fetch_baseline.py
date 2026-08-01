#!/usr/bin/env python3
"""Fetch or populate baseline raw data dumps into data/raw/ directory.

Supports offline copy from source directory via `--from <dir>`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
        "--from",
        "-f",
        dest="from_dir",
        type=Path,
        default=None,
        help="Copy raw dumps from a local directory (e.g. for offline test fixtures).",
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

    if opts.from_dir:
        from_path: Path = opts.from_dir.resolve()
        if not from_path.exists() or not from_path.is_dir():
            print(f"Error: source directory '{opts.from_dir}' not found at {from_path}")
            return 1

        json_files = list(from_path.glob("*.json"))
        if not json_files:
            print(f"Error: no JSON files found in source {from_path}")
            return 1

        for src in json_files:
            dst = output_dir / src.name
            if dst.exists() and not opts.force:
                print(f"Skipping {dst.name} (already exists, use --force to overwrite)")
                continue
            shutil.copy2(src, dst)
            print(f"Copied {src.name} -> {dst}")

        print(f"Successfully populated {output_dir} from source '{from_path}'")
        return 0

    # Non-fixture / default fetch fallback (offline placeholder)
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
