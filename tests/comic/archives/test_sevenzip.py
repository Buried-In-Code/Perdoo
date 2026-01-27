from pathlib import Path

import pytest

from perdoo.comic.archives import CB7Archive, CBZArchive
from perdoo.comic.archives.sevenzip import PY7ZR_AVAILABLE
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files

pytestmark = pytest.mark.skipif(not PY7ZR_AVAILABLE, reason="py7zr not installed")


def test_is_archive(cb7_path: Path) -> None:
    assert CB7Archive.is_archive(path=cb7_path) is True


def test_list_filenames(cb7_archive: CB7Archive) -> None:
    assert set(cb7_archive.list_filenames()) == {"info.txt", "001.jpg"}


def test_read_file(cb7_archive: CB7Archive) -> None:
    assert cb7_archive.read_file(filename="info.txt") == b"Fake data"
    assert cb7_archive.read_file(filename="001.jpg") == b"Fake image"


def test_unsupported_functions(cb7_archive: CB7Archive) -> None:
    with pytest.raises(ComicArchiveError, match=r"Unable to write"):
        cb7_archive.write_file(filename="info.txt", data=b"Updated data")
    with pytest.raises(ComicArchiveError, match=r"Unable to delete"):
        cb7_archive.delete_file(filename="info.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to rename"):
        cb7_archive.rename_file(filename="info.txt", new_name="new.txt")


def test_extract_files(cb7_archive: CB7Archive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cb7_archive.extract_files(destination=dest)

    assert (dest / "info.txt").read_text(encoding="UTF-8") == "Fake data"
    assert (dest / "001.jpg").read_bytes() == b"Fake image"


def test_archive_files(cb7_archive: CB7Archive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cb7_archive.extract_files(destination=dest)
    archive = CB7Archive.archive_files(
        src=dest, output_name=cb7_archive.filepath.stem, files=list_files(path=dest)
    )

    assert cb7_archive.filepath == archive


def test_convert_from(cbz_archive: CBZArchive) -> None:
    old_filenames = cbz_archive.list_filenames()
    archive = CB7Archive.convert_from(old_archive=cbz_archive)

    assert isinstance(archive, CB7Archive)
    assert archive.filepath.suffix == ".cb7"
    assert archive.filepath.exists()
    assert not cbz_archive.filepath.exists()
    assert archive.list_filenames() == old_filenames
    assert archive.read_file(filename="info.txt") == b"Fake data"
