from pathlib import Path

import pytest

from perdoo.comic.archives import CBTArchive, CBZArchive
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files


def test_is_archive(cbz_path: Path) -> None:
    assert CBZArchive.is_archive(path=cbz_path) is True


def test_list_filenames(cbz_archive: CBZArchive) -> None:
    assert set(cbz_archive.list_filenames()) == {"info.txt", "001.jpg"}


def test_read_file(cbz_archive: CBZArchive) -> None:
    assert cbz_archive.read_file(filename="info.txt") == b"Fake data"
    assert cbz_archive.read_file(filename="001.jpg") == b"Fake image"


def test_write_file(cbz_archive: CBZArchive) -> None:
    cbz_archive.write_file(filename="info.txt", data=b"Updated data")
    assert cbz_archive.read_file(filename="info.txt") == b"Updated data"

    assert "new.txt" not in cbz_archive.list_filenames()
    cbz_archive.write_file(filename="new.txt", data=b"Hello World")
    assert "new.txt" in cbz_archive.list_filenames()
    assert cbz_archive.read_file(filename="new.txt") == b"Hello World"


def test_delete_file(cbz_archive: CBZArchive) -> None:
    assert "info.txt" in cbz_archive.list_filenames()
    cbz_archive.delete_file(filename="info.txt")
    assert "info.txt" not in cbz_archive.list_filenames()
    cbz_archive.delete_file(filename="info.txt")
    assert "info.txt" not in cbz_archive.list_filenames()


def test_rename_file(cbz_archive: CBZArchive) -> None:
    cbz_archive.write_file(filename="new.txt", data=b"Hello World")
    with pytest.raises(ComicArchiveError, match=r"does not exist"):
        cbz_archive.rename_file(filename="missing.txt", new_name="new.txt")
    with pytest.raises(ComicArchiveError, match=r"already exists"):
        cbz_archive.rename_file(filename="new.txt", new_name="info.txt", override=False)

    cbz_archive.rename_file(filename="new.txt", new_name="info.txt", override=True)
    names = set(cbz_archive.list_filenames())
    assert "new.txt" not in names
    assert "info.txt" in names
    assert cbz_archive.read_file(filename="info.txt") == b"Hello World"


def test_extract_files(cbz_archive: CBZArchive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cbz_archive.extract_files(destination=dest)

    assert (dest / "info.txt").read_text(encoding="UTF-8") == "Fake data"
    assert (dest / "001.jpg").read_bytes() == b"Fake image"


def test_archive_files(cbz_archive: CBZArchive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cbz_archive.extract_files(destination=dest)
    archive = CBZArchive.archive_files(
        src=dest, output_name=cbz_archive.filepath.stem, files=list_files(path=dest)
    )

    assert cbz_archive.filepath == archive


def test_convert_from(cbt_archive: CBTArchive) -> None:
    old_filenames = cbt_archive.list_filenames()
    archive = CBZArchive.convert_from(old_archive=cbt_archive)

    assert isinstance(archive, CBZArchive)
    assert archive.filepath.suffix == ".cbz"
    assert archive.filepath.exists()
    assert not cbt_archive.filepath.exists()
    assert archive.list_filenames() == old_filenames
    assert archive.read_file(filename="info.txt") == b"Fake data"
