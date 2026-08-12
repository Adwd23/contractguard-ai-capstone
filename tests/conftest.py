from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from contractguard.config import Settings


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture()
def isolated_settings(tmp_path: Path, project_root: Path) -> Settings:
    (tmp_path / "data").mkdir()
    shutil.copytree(project_root / "data" / "policies", tmp_path / "data" / "policies")
    shutil.copytree(project_root / "data" / "samples", tmp_path / "data" / "samples")
    settings = Settings.from_env(tmp_path)
    settings.ensure_directories()
    return settings
