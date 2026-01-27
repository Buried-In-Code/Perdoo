from pathlib import Path
from typing import ClassVar

import pytest

from perdoo.comic.archives import Archive, CBTArchive, CBZArchive
from perdoo.comic.errors import ComicArchiveError


def test_load_selects_cbz(cbz_path: Path) -> None:
    loaded = Archive.load(filepath=cbz_path)

    assert isinstance(loaded, CBZArchive)
    assert loaded.filepath == cbz_path


def test_load_selects_cbt(cbt_path: Path) -> None:
    loaded = Archive.load(filepath=cbt_path)

    assert isinstance(loaded, CBTArchive)
    assert loaded.filepath == cbt_path


def test_load_unsupported(tmp_path: Path) -> None:
    tmp = tmp_path / "sample.xyz"
    tmp.write_bytes(b"Unsupported")

    with pytest.raises(ComicArchiveError, match=r"Unsupported archive format"):
        Archive.load(filepath=tmp)


def test_default_operations(tmp_path: Path, cbz_archive: CBZArchive) -> None:
    class DummyArchive(Archive):
        EXTENSION: ClassVar[str] = ".xyz"
        IS_READABLE: ClassVar[bool] = False
        IS_WRITEABLE: ClassVar[bool] = False
        IS_EDITABLE: ClassVar[bool] = False

        @classmethod
        def is_archive(cls, path: Path) -> bool:  # noqa: ARG003
            return False

        def list_filenames(self) -> list[str]:
            return []

        def extract_files(self, destination: Path) -> None:  # noqa: ARG002
            return None

    tmp = DummyArchive(filepath=tmp_path / "sample.xyz")
    with pytest.raises(ComicArchiveError, match=r"Unable to read"):
        tmp.read_file(filename="info.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to write"):
        tmp.write_file(filename="info.txt", data=b"Hello World")
    with pytest.raises(ComicArchiveError, match=r"Unable to delete"):
        tmp.delete_file(filename="info.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to rename"):
        tmp.rename_file(filename="info.txt", new_name="new.txt")
    with pytest.raises(ComicArchiveError, match=r"Unable to archive"):
        DummyArchive.archive_files(src=tmp_path, output_name="sample", files=[])
    with pytest.raises(ComicArchiveError, match=r"Unable to convert"):
        DummyArchive.convert_from(old_archive=cbz_archive)
