from pathlib import Path

import pytest


@pytest.fixture
def case_sensitive_fs(tmp_path: Path) -> None:
    probe = tmp_path / "case-probe.tmp"
    probe.touch()
    try:
        if (tmp_path / "CASE-PROBE.TMP").exists():
            pytest.skip("the filesystem is case-insensitive")
    finally:
        probe.unlink()
