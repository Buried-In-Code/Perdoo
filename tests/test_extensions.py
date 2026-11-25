import zipfile
from pathlib import Path

import pytest
from shortbox import Comic
from shortbox.metadata import ComicInfo

from perdoo.cli._runner import Outcome
from perdoo.cli.rename import rename_comic, rename_entry
from perdoo.settings import Settings


@pytest.fixture(autouse=True)
def _isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CONFIG", "DATA", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / "xdg" / name.lower()))


def _cbz(folder: Path, names: list[str]) -> Path:
    file = folder / "comic.cbz"
    with zipfile.ZipFile(file, "w") as archive:
        for name in names:
            archive.writestr(name, b"data")
    return file


def test_rename_standardizes_page_extensions(tmp_path: Path) -> None:
    file = _cbz(tmp_path, ["a.png", "b.PNG", "c.jpg", "d.JPEG", "ComicInfo.xml"])

    with Comic.open(file=file) as comic:
        renamed = rename_comic(comic=comic, image_exts=(".png", ".jpg", ".jpeg"))
    with Comic.open(file=file) as comic:
        names = comic.list_filenames()

    assert renamed
    assert names == ["0.png", "1.png", "2.jpg", "3.jpg", "ComicInfo.xml"]


def _tagged_cbz(file: Path) -> Path:
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("a.PNG", b"data")
        archive.writestr("b.JPEG", b"data")
    with Comic.open(file=file) as comic:
        comic.set_metadata(ComicInfo(series="Test Series", number="1", title="T", year=2020))
    return file


def test_rename_entry_standardizes_archive_and_page_extensions(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    file = _tagged_cbz(tmp_path / "Some Comic.CBZ")
    settings = Settings()
    settings.output.folder = library

    outcome = rename_entry(entry=file, target=tmp_path, settings=settings)

    new_file = library / "Test-Series" / "Test-Series_#001.cbz"
    assert outcome is Outcome.SUCCESS
    assert new_file.exists()
    assert not file.exists()
    with Comic.open(file=new_file) as comic:
        assert comic.list_filenames() == ["0.png", "1.jpg", "ComicInfo.xml"]


def test_rename_entry_fixes_a_case_only_difference_in_place(tmp_path: Path) -> None:
    library = tmp_path / "library"
    folder = library / "Test-Series"
    folder.mkdir(parents=True)
    file = _tagged_cbz(folder / "Test-Series_#001.CBZ")
    settings = Settings()
    settings.output.folder = library

    outcome = rename_entry(entry=file, target=library, settings=settings)

    assert outcome is Outcome.SUCCESS
    assert [x.name for x in folder.iterdir()] == ["Test-Series_#001.cbz"]
