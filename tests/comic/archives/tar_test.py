from pathlib import Path

import pytest

from perdoo.comic.archives import CBTArchive, CBZArchive
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files


def test_is_archive(cbt_path: Path) -> None:
    assert CBTArchive.is_archive(path=cbt_path) is True


def test_list_filenames(cbt_archive: CBTArchive) -> None:
    assert set(cbt_archive.list_filenames()) == {"info.txt", "001.jpg"}


def test_unsupported_functions(cbt_archive: CBTArchive) -> None:
    with pytest.raises(ComicArchiveError, match=r"Unable to read"):
        cbt_archive.read_file(filename="info.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to write"):
        cbt_archive.write_file(filename="info.txt", data=b"Updated data")
    with pytest.raises(ComicArchiveError, match=r"Unable to delete"):
        cbt_archive.delete_file(filename="info.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to rename"):
        cbt_archive.rename_file(filename="info.txt", new_name="new.txt")


def test_extract_files(cbt_archive: CBTArchive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cbt_archive.extract_files(destination=dest)

    assert (dest / "info.txt").read_text(encoding="UTF-8") == "Fake data"
    assert (dest / "001.jpg").read_bytes() == b"Fake image"


def test_archive_files(cbt_archive: CBTArchive, tmp_path: Path) -> None:
    dest = tmp_path / "out"
    dest.mkdir(parents=True, exist_ok=True)
    cbt_archive.extract_files(destination=dest)
    archive = CBTArchive.archive_files(
        src=dest, output_name=cbt_archive.filepath.stem, files=list_files(path=dest)
    )

    assert cbt_archive.filepath == archive


def test_convert_from(cbz_archive: CBZArchive) -> None:
    old_filenames = cbz_archive.list_filenames()
    archive = CBTArchive.convert_from(old_archive=cbz_archive)

    assert isinstance(archive, CBTArchive)
    assert archive.filepath.suffix == ".cbt"
    assert archive.filepath.exists()
    assert not cbz_archive.filepath.exists()
    assert archive.list_filenames() == old_filenames
    # TODO: assert archive.read_file(filename="info.txt") == b"Fake data"
