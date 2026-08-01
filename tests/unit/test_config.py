from pathlib import Path

from npc_planner import __version__
from npc_planner.config import get_settings


def test_package_version() -> None:
    assert __version__ == "0.1.0a1"


def test_get_settings_default() -> None:
    settings = get_settings()
    assert settings.project_root.exists()
    assert settings.data_raw_dir == settings.project_root / "data" / "raw"
    assert settings.data_hack_dir == settings.project_root / "data" / "hack"
    assert settings.data_rulesets_dir == settings.project_root / "data" / "rulesets"
    assert settings.data_processed_dir == settings.project_root / "data" / "processed"
    assert settings.config_dir == settings.project_root / "config"
    assert settings.exports_dir == settings.project_root / "exports"


def test_get_settings_custom_root(tmp_path: Path) -> None:
    custom_settings = get_settings(root=tmp_path)
    assert custom_settings.project_root == tmp_path
    assert custom_settings.data_raw_dir == tmp_path / "data" / "raw"
