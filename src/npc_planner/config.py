from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_root: Path
    data_raw_dir: Path
    data_hack_dir: Path
    data_rulesets_dir: Path
    data_processed_dir: Path
    config_dir: Path
    exports_dir: Path

    model_config = SettingsConfigDict(arbitrary_types_allowed=True)


def get_settings(root: Path | None = None) -> Settings:
    if root is None:
        root = Path(__file__).resolve().parents[2]

    return Settings(
        project_root=root,
        data_raw_dir=root / "data" / "raw",
        data_hack_dir=root / "data" / "hack",
        data_rulesets_dir=root / "data" / "rulesets",
        data_processed_dir=root / "data" / "processed",
        config_dir=root / "config",
        exports_dir=root / "exports",
    )
