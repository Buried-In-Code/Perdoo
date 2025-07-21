from pathlib import Path
from unittest.mock import MagicMock

import pytest

from perdoo.comic import Comic, ComicMetadataError
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.metron_info import Series
from perdoo.settings import Naming


@pytest.fixture
def cbz_comic(tmp_path: Path) -> Comic:
    file_path = tmp_path / "test.cbz"
    file_path.touch()
    return Comic(file=file_path)


@pytest.fixture
def cbt_comic(tmp_path: Path) -> Comic:
    file_path = tmp_path / "test.cbt"
    file_path.touch()
    return Comic(file=file_path)


@pytest.fixture
def metron_info() -> MetronInfo:
    return MetronInfo(series=Series(name="Test Series"))


@pytest.fixture
def comic_info() -> ComicInfo:
    return ComicInfo()


def test_convert_to_cbz(cbt_comic: Comic) -> None:
    cbt_comic.convert_to_cbz()
    assert cbt_comic.path.suffix == ".cbz"


def test_clean_archive(cbz_comic: Comic) -> None:
    cbz_comic._archiver.get_filename_list = MagicMock(  # noqa: SLF001
        return_value=["image1.jpg", "info.txt", "ComicInfo.xml", "cover.png"]
    )
    cbz_comic._archiver.remove_files = MagicMock()  # noqa: SLF001

    cbz_comic.clean_archive()
    cbz_comic._archiver.remove_files.assert_called_once()  # noqa: SLF001
    cbz_comic._archiver.remove_files.assert_called_once_with(filename_list=["info.txt"])  # noqa: SLF001


def test_write_comicinfo(cbz_comic: Comic, comic_info: ComicInfo) -> None:
    assert cbz_comic.comic_info is None
    cbz_comic.write_metadata(metadata=comic_info)
    assert cbz_comic.comic_info == comic_info


def test_write_metroninfo(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    assert cbz_comic.metron_info is None
    cbz_comic.write_metadata(metadata=metron_info)
    assert cbz_comic.metron_info == metron_info


def test_write_null_metadata(cbz_comic: Comic) -> None:
    with pytest.raises(ComicMetadataError):
        cbz_comic.write_metadata(metadata=None)
    assert cbz_comic.comic_info is None
    assert cbz_comic.metron_info is None


def test_write_metadata_override(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    metadata_copy = metron_info.model_copy(deep=True)
    metadata_copy.series.volume = 2

    assert cbz_comic.metron_info is None
    cbz_comic.write_metadata(metadata=metron_info)
    assert cbz_comic.metron_info == metron_info
    cbz_comic.write_metadata(metadata=metadata_copy)
    assert cbz_comic.metron_info == metadata_copy


def test_rename(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    cbz_comic.write_metadata(metadata=metron_info)
    cbz_comic.rename(naming=Naming(), output_folder=cbz_comic.path.parent)
    assert cbz_comic.path.name == "Test-Series-v1_#.cbz"
