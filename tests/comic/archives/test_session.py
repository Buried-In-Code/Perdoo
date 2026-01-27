import pytest

from perdoo.comic.archives import ArchiveSession, CBTArchive, CBZArchive
from perdoo.comic.errors import ComicArchiveError


def test_editable_session(cbz_archive: CBZArchive) -> None:
    with ArchiveSession(archive=cbz_archive) as session:
        assert session.contains(filename="info.txt")
        assert session.read(filename="info.txt") == b"Fake data"

        session.write(filename="info.txt", data="Updated data")
        session.write(filename="src.txt", data=b"Hello World")
        session.rename(filename="src.txt", new_name="new.txt")
        session.delete(filename="001.jpg")

        assert cbz_archive.read_file(filename="info.txt") == b"Updated data"
        assert "001.jpg" not in cbz_archive.list_filenames()
        assert "src.txt" not in cbz_archive.list_filenames()
        assert "new.txt" in cbz_archive.list_filenames()


def test_non_editable_session(cbt_archive: CBTArchive) -> None:
    with ArchiveSession(archive=cbt_archive) as session:
        assert session.contains(filename="info.txt")
        assert session.read(filename="info.txt") == b"Fake data"

        session.write(filename="info.txt", data="Updated data")
        session.write(filename="src.txt", data=b"Hello World")
        session.rename(filename="src.txt", new_name="new.txt")
        session.delete(filename="001.jpg")

        # TODO: assert cbt_archive.read_file(filename="info.txt") != b"Updated data"
        assert "001.jpg" in cbt_archive.list_filenames()
        assert "src.txt" not in cbt_archive.list_filenames()
        assert "new.txt" not in cbt_archive.list_filenames()


def test_session_rename_raises_exception(cbz_archive: CBZArchive) -> None:
    with ArchiveSession(cbz_archive) as session:
        with pytest.raises(ComicArchiveError, match=r"Unable to rename"):
            session.rename(filename="new.txt", new_name="info.txt")
        with pytest.raises(ComicArchiveError, match=r"Unable to rename"):
            session.rename(filename="info.txt", new_name="001.jpg", override=False)
