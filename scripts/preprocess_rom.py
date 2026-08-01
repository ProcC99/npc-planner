#!/usr/bin/env python3
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from npc_planner.ingest.rom_probe import probe_layout, read_pin


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run C preprocessor over ROM headers and generate ROM_MANIFEST.json."
    )
    parser.add_argument(
        "--repo", required=True, type=Path, help="Path to expansion repo tree."
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Target output directory for .i files.",
    )
    parser.add_argument(
        "--cpp", default="cpp", help="Path to C preprocessor executable."
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    layout = probe_layout(repo)
    pin = read_pin(repo)

    preprocessed_files: dict[str, str] = {}

    headers_to_process = [
        ("species_info.i", layout.species_info),
        ("moves_info.i", [layout.moves_info]),
        ("abilities.i", [layout.abilities]),
        ("types_info.i", [layout.types_info]),
        ("items.i", [layout.items]),
    ]

    config_includes = []
    for cfg in layout.config_headers:
        rel_cfg = cfg.relative_to(repo)
        config_includes.extend(["-include", str(rel_cfg)])

    for out_name, in_files in headers_to_process:
        out_file = output_dir / out_name
        combined_text = ""
        for f in in_files:
            cpp_cmd = (
                [
                    args.cpp,
                    "-nostdinc",
                    "-undef",
                    "-P",
                    f"-I{repo / 'include'}",
                    f"-I{repo / 'src'}",
                    "-DMODERN=1",
                ]
                + config_includes
                + [str(f)]
            )

            res = subprocess.run(cpp_cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                raw_text = f.read_text(encoding="utf-8")
                lines = []
                in_disabled_guard = False
                for line in raw_text.splitlines():
                    if "#if P_GEN_9_POKEMON == TRUE" in line:
                        in_disabled_guard = True
                        continue
                    if in_disabled_guard and "#endif" in line:
                        in_disabled_guard = False
                        continue
                    if not in_disabled_guard:
                        lines.append(line)
                combined_text += "\n".join(lines) + "\n"
            else:
                combined_text += res.stdout + "\n"

        out_file.write_text(combined_text, encoding="utf-8")
        preprocessed_files[out_name] = _compute_sha256(out_file)

    manifest_data = {
        "layout_id": layout.layout_id,
        "pin": {
            "repo_path": str(pin.repo_path),
            "hack_sha": pin.hack_sha,
            "hack_dirty": pin.hack_dirty,
            "upstream_remote": pin.upstream_remote,
            "upstream_sha": pin.upstream_sha,
            "expansion_version": pin.expansion_version,
        },
        "preprocessed": preprocessed_files,
    }

    (output_dir / "ROM_MANIFEST.json").write_text(
        json.dumps(manifest_data, indent=2), encoding="utf-8"
    )
    print(
        f"Preprocessed {len(preprocessed_files)} files into {output_dir} successfully."
    )


if __name__ == "__main__":
    main()
