from pathlib import Path

import pytest

from perdoo.comic.archives import CB7Archive, CBTArchive, CBZArchive


@pytest.fixture
def archive_files() -> dict[str, bytes]:
    return {"info.txt": b"Fake data", "001.jpg": b"Fake image"}


@pytest.fixture
def src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)
    return src


@pytest.fixture
def cbz_path(src: Path, archive_files: dict[str, bytes]) -> Path:
    created: list[Path] = []
    for filename, data in archive_files.items():
        tmp = src / filename
        tmp.write_bytes(data)
        created.append(tmp)
    return CBZArchive.archive_files(src=src, output_name="sample", files=created)


@pytest.fixture
def cbz_archive(cbz_path: Path) -> CBZArchive:
    return CBZArchive(filepath=cbz_path)


@pytest.fixture
def cbt_path(src: Path, archive_files: dict[str, bytes]) -> Path:
    created: list[Path] = []
    for filename, data in archive_files.items():
        tmp = src / filename
        tmp.write_bytes(data)
        created.append(tmp)
    return CBTArchive.archive_files(src=src, output_name="sample", files=created)


@pytest.fixture
def cbt_archive(cbt_path: Path) -> CBTArchive:
    return CBTArchive(filepath=cbt_path)


@pytest.fixture
def cb7_path(src: Path, archive_files: dict[str, bytes]) -> Path:
    created: list[Path] = []
    for filename, data in archive_files.items():
        tmp = src / filename
        tmp.write_bytes(data)
        created.append(tmp)
    return CB7Archive.archive_files(src=src, output_name="sample", files=created)


@pytest.fixture
def cb7_archive(cb7_path: Path) -> CB7Archive:
    return CB7Archive(filepath=cb7_path)
