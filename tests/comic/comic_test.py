from unittest.mock import MagicMock

import pytest

from perdoo.cli.process import generate_naming
from perdoo.comic.archives import CBTArchive, CBZArchive
from perdoo.comic.comic import Comic
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.settings import Naming


@pytest.fixture
def cbz_comic(cbz_archive: CBZArchive) -> Comic:
    return Comic(filepath=cbz_archive.filepath)


@pytest.fixture
def cbt_comic(cbt_archive: CBTArchive) -> Comic:
    return Comic(filepath=cbt_archive.filepath)


def test_convert_to_cbz(cbt_comic: Comic) -> None:
    cbt_comic.convert_to(extension="cbz")
    assert isinstance(cbt_comic.archive, CBZArchive)
    assert cbt_comic.filepath.suffix == ".cbz"


def test_convert_to_cbt(cbz_comic: Comic) -> None:
    cbz_comic.convert_to(extension="cbt")
    assert isinstance(cbz_comic.archive, CBTArchive)
    assert cbz_comic.filepath.suffix == ".cbt"


def test_clean_archive(cbz_comic: Comic) -> None:
    cbz_comic.archive.list_filenames = MagicMock(
        return_value=["001.jpg", "info.txt", "ComicInfo.xml", "cover.png"]
    )
    cbz_comic.archive.delete_file = MagicMock()
    with cbz_comic.open_session() as session:
        for extra in cbz_comic.list_extras():
            session.delete(filename=extra.name)
    cbz_comic.archive.delete_file.assert_called_once_with(filename="info.txt")


def test_write_comicinfo(cbz_comic: Comic, comic_info: ComicInfo) -> None:
    with cbz_comic.open_session() as session:
        _, info = cbz_comic.read_metadata(session=session)
        assert info is None
        session.write(filename=ComicInfo.FILENAME, data=comic_info.to_bytes())
        _, info = cbz_comic.read_metadata(session=session)
        assert info == comic_info


def test_write_metroninfo(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    with cbz_comic.open_session() as session:
        info, _ = cbz_comic.read_metadata(session=session)
        assert info is None
        session.write(filename=MetronInfo.FILENAME, data=metron_info.to_bytes())
        info, _ = cbz_comic.read_metadata(session=session)
        assert info == metron_info


def test_write_metadata_override(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    metadata_copy = metron_info.model_copy(deep=True)
    metadata_copy.series.volume = 2

    with cbz_comic.open_session() as session:
        info, _ = cbz_comic.read_metadata(session=session)
        assert info is None
        session.write(filename=MetronInfo.FILENAME, data=metron_info.to_bytes())
        info, _ = cbz_comic.read_metadata(session=session)
        assert info == metron_info
        session.write(filename=MetronInfo.FILENAME, data=metadata_copy.to_bytes())
        info, _ = cbz_comic.read_metadata(session=session)
        assert info == metadata_copy


def test_rename(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    naming = generate_naming(settings=Naming(), metron_info=metron_info, comic_info=None)
    cbz_comic.move_to(naming=naming, output_folder=cbz_comic.filepath.parent)
    assert cbz_comic.filepath.name == "Test-Series-v1_#.cbz"
