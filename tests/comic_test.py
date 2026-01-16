import tarfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from zipremove import ZipFile

from perdoo.comic import Comic
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.metron_info import Series
from perdoo.settings import Naming


@pytest.fixture
def image_file(tmp_path: Path) -> Path:
    filepath = tmp_path / "page1.jpg"
    filepath.write_bytes(b"Fake image")
    return filepath


@pytest.fixture
def cbz_comic(tmp_path: Path, image_file: Path) -> Comic:
    filepath = tmp_path / "test.cbz"
    with ZipFile(filepath, "w") as archive:
        archive.write(image_file)
    return Comic(filepath=filepath)


@pytest.fixture
def cbt_comic(tmp_path: Path, image_file: Path) -> Comic:
    filepath = tmp_path / "test.cbt"
    with tarfile.open(filepath, "w:gz") as archive:
        archive.add(image_file)
    return Comic(filepath=filepath)


@pytest.fixture
def metron_info() -> MetronInfo:
    return MetronInfo(series=Series(name="Test Series"))


@pytest.fixture
def comic_info() -> ComicInfo:
    return ComicInfo()


def test_convert_to_cbz(cbt_comic: Comic) -> None:
    cbt_comic.convert_to(extension="cbz")
    assert cbt_comic.filepath.suffix == ".cbz"


def test_clean_archive(cbz_comic: Comic) -> None:
    cbz_comic.archive.list_filenames = MagicMock(
        return_value=["image1.jpg", "info.txt", "ComicInfo.xml", "cover.png"]
    )
    cbz_comic.archive.remove_file = MagicMock()

    cbz_comic.clean_archive()
    cbz_comic.archive.remove_file.assert_called_once()
    cbz_comic.archive.remove_file.assert_called_once_with(filename="info.txt")


def test_write_comicinfo(cbz_comic: Comic, comic_info: ComicInfo) -> None:
    assert cbz_comic.comic_info is None
    cbz_comic.write_metadata(metadata=comic_info)
    assert cbz_comic.comic_info == comic_info


def test_write_metroninfo(cbz_comic: Comic, metron_info: MetronInfo) -> None:
    assert cbz_comic.metron_info is None
    cbz_comic.write_metadata(metadata=metron_info)
    assert cbz_comic.metron_info == metron_info


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
    cbz_comic.rename(naming=Naming(), output_folder=cbz_comic.filepath.parent)
    assert cbz_comic.filepath.name == "Test-Series-v1_#.cbz"
