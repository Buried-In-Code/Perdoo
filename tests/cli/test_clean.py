import io
import tarfile
import zipfile
from pathlib import Path

import pytest
from shortbox import Comic

from perdoo.cli._runner import Outcome
from perdoo.cli.clean import clean_comic
from perdoo.settings import Settings


def _cbz(folder: Path, names: list[str]) -> Path:
    file = folder / "comic.cbz"
    with zipfile.ZipFile(file, "w") as archive:
        for name in names:
            archive.writestr(name, b"" if name.endswith("/") else b"data")
    return file


def _clean(file: Path, targets: list[str], dry_run: bool = False) -> tuple[Outcome, list[str]]:
    with Comic.open(file=file) as comic:
        outcome = clean_comic(comic=comic, removals=targets, dry_run=dry_run)
    with Comic.open(file=file) as comic:
        return outcome, comic.list_filenames()


def test_default_clean_targets() -> None:
    assert tuple(Settings().removals) == ("*.nfo", "*.sfv", "*.db", ".DS_Store")


@pytest.mark.parametrize(
    ("targets", "expected"),
    [
        (["*.nfo"], ["001.png", "sub/page.png", "sub/.DS_Store", ".DS_Store"]),
        ([".DS_Store"], ["001.png", "a.nfo", "sub/b.nfo", "sub/page.png"]),
        (["/a.nfo"], ["001.png", "sub/b.nfo", "sub/page.png", "sub/.DS_Store", ".DS_Store"]),
        (
            ["*.nfo", "!sub/b.nfo"],
            ["001.png", "sub/b.nfo", "sub/page.png", "sub/.DS_Store", ".DS_Store"],
        ),
        (["sub/"], ["001.png", "a.nfo", ".DS_Store"]),
        (["**/page.png"], ["001.png", "a.nfo", "sub/b.nfo", "sub/.DS_Store", ".DS_Store"]),
    ],
    ids=["extension", "dotfile-any-depth", "anchored", "negation", "folder", "glob"],
)
def test_clean_comic_matches_gitignore_patterns(
    targets: list[str], expected: list[str], tmp_path: Path
) -> None:
    file = _cbz(
        tmp_path, ["001.png", "a.nfo", "sub/b.nfo", "sub/page.png", "sub/.DS_Store", ".DS_Store"]
    )

    outcome, names = _clean(file, targets)

    assert outcome is Outcome.SUCCESS
    assert sorted(names) == sorted(expected)


def test_clean_comic_removes_a_folder_and_its_directory_entries(tmp_path: Path) -> None:
    file = _cbz(
        tmp_path,
        [
            "001.png",
            "unwanted-folder/",
            "unwanted-folder/a.png",
            "unwanted-folder/sub/",
            "unwanted-folder/sub/b.png",
        ],
    )

    outcome, names = _clean(file, ["unwanted-folder/"])

    assert outcome is Outcome.SUCCESS
    assert names == ["001.png"]


def test_clean_comic_does_not_match_a_file_named_like_a_folder(tmp_path: Path) -> None:
    file = _cbz(tmp_path, ["001.png", "unwanted-folder"])

    outcome, names = _clean(file, ["unwanted-folder/"])

    assert outcome is Outcome.UNCHANGED
    assert names == ["001.png", "unwanted-folder"]


def test_clean_comic_is_case_sensitive_like_gitignore(tmp_path: Path) -> None:
    file = _cbz(tmp_path, ["001.png", "a.nfo", "B.NFO", ".ds_store"])

    outcome, names = _clean(file, ["*.nfo", ".DS_Store"])

    assert outcome is Outcome.SUCCESS
    assert sorted(names) == sorted(["001.png", "B.NFO", ".ds_store"])


def test_clean_comic_is_unchanged_without_matches(tmp_path: Path) -> None:
    file = _cbz(tmp_path, ["001.png"])

    outcome, names = _clean(file, ["*.nfo"])

    assert outcome is Outcome.UNCHANGED
    assert names == ["001.png"]


def test_clean_comic_dry_run_changes_nothing(tmp_path: Path) -> None:
    file = _cbz(tmp_path, ["001.png", "a.nfo", "unwanted-folder/b.png"])
    before = file.read_bytes()

    outcome, names = _clean(file, ["*.nfo", "unwanted-folder/"], dry_run=True)

    assert outcome is Outcome.SUCCESS
    assert file.read_bytes() == before
    assert names == ["001.png", "a.nfo", "unwanted-folder/b.png"]


def test_clean_comic_works_on_tar_archives(tmp_path: Path) -> None:
    file = tmp_path / "comic.cbt"
    with tarfile.open(file, "w") as archive:
        for name in ("001.png", "a.nfo", ".DS_Store"):
            info = tarfile.TarInfo(name)
            info.size = 4
            archive.addfile(info, io.BytesIO(b"data"))

    outcome, names = _clean(file, ["*.nfo", ".DS_Store"])

    assert outcome is Outcome.SUCCESS
    assert names == ["001.png"]
