from argparse import Namespace
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from perdoo.cli.convert.image import run as run_images
from PIL import Image
from shortbox import Comic
from shortbox.archives import TarArchive
from shortbox.errors import UnsupportedArchiveError

from perdoo.cli import build_parser, pipeline
from perdoo.cli._runner import Outcome
from perdoo.cli.convert.archive import convert_entry, run as run_archive
from perdoo.formats import ArchiveFormat, ImageFormat
from perdoo.settings import Settings


def _settings(image_format: ImageFormat | None = ImageFormat.JPG) -> Settings:
    settings = Settings()
    settings.output.image_format = image_format
    return settings


@pytest.fixture(autouse=True)
def _isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CONFIG", "DATA", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / "xdg" / name.lower()))


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (["archive"], run_archive),
        (["images"], run_images),
        (["images", "-i", "cbr"], run_images),
        (["archive", "--dry-run"], run_archive),
    ],
    ids=["archive", "images", "images-with-option", "archive-dry-run"],
)
def test_convert_dispatches_to_the_right_step(
    arguments: list[str], expected: object, tmp_path: Path
) -> None:
    target = tmp_path / "Mixed Case Folder"
    target.mkdir()

    args = build_parser().parse_args(["convert", *arguments, str(target)])

    assert args.func is expected
    assert args.target == target.resolve()


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--dry-run"],
        ["all"],
        ["{target}"],
        ["-i", "cbr", "{target}"],
        ["--dry-run", "{target}"],
    ],
    ids=["nothing", "only-flag", "all", "bare-target", "bare-target-with-option", "bare-dry-run"],
)
def test_convert_requires_a_subcommand(arguments: list[str], tmp_path: Path) -> None:
    arguments = [x.format(target=tmp_path) for x in arguments]

    with pytest.raises(SystemExit):
        build_parser().parse_args(["convert", *arguments])


def test_convert_help_lists_only_the_two_steps(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as err:
        build_parser().parse_args(["convert", "--help"])

    output = capsys.readouterr().out
    assert err.value.code == 0
    assert "{archive,images}" in output
    assert "all" not in output.split("{archive,images}")[1].split("Options")[0].split()


def _cbt(folder: Path) -> Path:
    page = BytesIO()
    Image.new("RGB", (16, 16), (200, 10, 10)).save(page, format="PNG")
    source = folder / "src" / "001.png"
    source.parent.mkdir()
    source.write_bytes(page.getvalue())
    return TarArchive.archive_files(parent=folder, name="comic", files=[source])


def test_convert_entry_converts_other_formats(tmp_path: Path) -> None:
    file = _cbt(tmp_path)

    outcome, new_file = convert_entry(entry=file, archive_format=ArchiveFormat.CBZ, dry_run=False)

    assert outcome is Outcome.SUCCESS
    assert new_file == tmp_path / "comic.cbz"
    assert new_file.exists()
    assert not file.exists()


def test_convert_entry_leaves_the_target_format_alone(tmp_path: Path) -> None:
    file = _cbt(tmp_path)

    outcome, new_file = convert_entry(entry=file, archive_format=ArchiveFormat.CBT, dry_run=False)

    assert outcome is Outcome.UNCHANGED
    assert new_file == file


def test_convert_entry_standardizes_the_extension_case(tmp_path: Path) -> None:
    file = _cbt(tmp_path)
    upper = file.rename(file.with_suffix(".CBT"))
    before = upper.read_bytes()

    outcome, new_file = convert_entry(entry=upper, archive_format=ArchiveFormat.CBT, dry_run=False)

    assert outcome is Outcome.SUCCESS
    assert new_file == tmp_path / "comic.cbt"
    assert new_file.read_bytes() == before
    assert [x.name for x in tmp_path.iterdir() if x.is_file()] == ["comic.cbt"]


def test_convert_entry_never_overwrites_when_standardizing(tmp_path: Path) -> None:
    file = _cbt(tmp_path)
    upper = tmp_path / "comic.CBT"
    upper.write_bytes(file.read_bytes())
    original = file.read_bytes()

    outcome, new_file = convert_entry(entry=upper, archive_format=ArchiveFormat.CBT, dry_run=False)

    assert outcome is Outcome.SKIPPED
    assert new_file == upper
    assert upper.exists()
    assert file.read_bytes() == original


@pytest.mark.parametrize("suffix", [".cbt", ".CBT"])
@pytest.mark.parametrize("target", [ArchiveFormat.CBZ, ArchiveFormat.CBT])
def test_convert_entry_dry_run_changes_nothing(
    suffix: str, target: ArchiveFormat, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = _cbt(tmp_path)
    file = file.rename(file.with_suffix(suffix))
    before = {x.name: x.read_bytes() for x in tmp_path.iterdir() if x.is_file()}

    outcome, new_file = convert_entry(entry=file, archive_format=target, dry_run=True)

    assert new_file == file
    assert {x.name: x.read_bytes() for x in tmp_path.iterdir() if x.is_file()} == before
    expected = Outcome.UNCHANGED if file.suffix == target.extension else Outcome.SUCCESS
    assert outcome is expected
    if expected is Outcome.SUCCESS:
        assert "Would " in capsys.readouterr().out


def test_convert_entry_rejects_files_that_are_not_archives(tmp_path: Path) -> None:
    page = tmp_path / "cover.jpg"
    page.write_bytes(b"not an archive")

    with pytest.raises(UnsupportedArchiveError):
        convert_entry(entry=page, archive_format=ArchiveFormat.CBZ, dry_run=False)


def test_convert_archive_dry_run_leaves_everything_in_place(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = _cbt(tmp_path)
    before = file.read_bytes()
    args = Namespace(target=file.resolve(), ignore=None, dry_run=True)

    run_archive(args, Settings())

    assert file.read_bytes() == before
    assert [x.name for x in tmp_path.iterdir() if x.is_file()] == ["comic.cbt"]
    assert args.target == file.resolve()
    assert "Would convert 'comic.cbt' to 'comic.cbz'" in capsys.readouterr().out


def test_convert_images_alone_does_not_convert_archives(tmp_path: Path) -> None:
    file = _cbt(tmp_path)
    args = Namespace(target=file.resolve(), ignore=None, dry_run=False)

    run_images(args, _settings())

    assert file.exists()
    assert not (tmp_path / "comic.cbz").exists()
    with Comic.open(file=file) as comic:
        assert comic.list_filenames() == ["001.jpg"]


def test_pipeline_runs_both_convert_steps_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def spy(name: str, original: Callable[[Namespace, Settings], None] | None = None) -> Callable:
        def step(args: Namespace, settings: Settings) -> None:
            calls.append(name)
            if original:
                original(args, settings)

        return step

    for name in ("run_convert_archive", "run_convert_images"):
        monkeypatch.setattr(pipeline, name, spy(name, getattr(pipeline, name)))
    for name in ("run_clean", "run_sync", "run_rename"):
        monkeypatch.setattr(pipeline, name, spy(name))
    file = _cbt(tmp_path)
    args = Namespace(target=file.resolve(), ignore=None, dry_run=False)

    pipeline.run(args)

    assert calls == [
        "run_convert_archive",
        "run_convert_images",
        "run_clean",
        "run_sync",
        "run_rename",
    ]
    with Comic.open(file=tmp_path / "comic.cbz") as comic:
        assert comic.list_filenames() == ["001.jpg"]


def test_convert_images_is_skipped_without_an_image_format(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = _cbt(tmp_path)
    before = file.read_bytes()
    args = Namespace(target=file.resolve(), ignore=None, dry_run=False)

    run_images(args, _settings(image_format=None))

    output = " ".join(capsys.readouterr().out.split())
    assert file.read_bytes() == before
    assert "Skipping image conversion" in output
    assert "output.image-format" in output
    assert "jpg, png, webp, jxl" in output
    assert "Summary" not in output


def test_pipeline_converts_archives_but_skips_images_without_an_image_format(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("run_clean", "run_sync", "run_rename"):
        monkeypatch.setattr(pipeline, name, lambda *_: None)
    file = _cbt(tmp_path)
    args = Namespace(target=file.resolve(), ignore=None, dry_run=False)

    pipeline.run(args)

    assert "Skipping image conversion" in capsys.readouterr().out
    with Comic.open(file=tmp_path / "comic.cbz") as comic:
        assert comic.list_filenames() == ["001.png"]
