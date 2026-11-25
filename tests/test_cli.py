from argparse import ArgumentParser, _SubParsersAction
from collections.abc import Iterator
from pathlib import Path

import pytest
from rich_argparse import HelpPreviewAction

from perdoo.cli import build_parser
from perdoo.cli._runner import collect_files
from perdoo.formats import ArchiveType


def _preview_paths(parser: ArgumentParser) -> Iterator[str]:
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, HelpPreviewAction):
            yield action.const
        if isinstance(action, _SubParsersAction):
            for child in {id(x): x for x in action.choices.values()}.values():
                yield from _preview_paths(child)


def test_help_previews_are_named_after_their_command() -> None:
    expected = {
        "perdoo",
        "perdoo_archive",
        "perdoo_archive_comic-info",
        "perdoo_archive_metron-info",
        "perdoo_archive_remove",
        "perdoo_archive_tree",
        "perdoo_clean",
        "perdoo_convert",
        "perdoo_convert_archive",
        "perdoo_convert_images",
        "perdoo_pipeline",
        "perdoo_rename",
        "perdoo_settings",
        "perdoo_sync",
    }

    assert set(_preview_paths(build_parser())) == {f"docs/img/{x}.svg" for x in expected}


@pytest.mark.parametrize(
    "command",
    [["clean"], ["pipeline"], ["rename"], ["sync"], ["convert", "archive"], ["convert", "images"]],
    ids=" ".join,
)
def test_commands_share_target_and_ignore_arguments(command: list[str], tmp_path: Path) -> None:
    args = build_parser().parse_args([*command, "-i", "CBR", "--ignore", "pdf", str(tmp_path)])

    assert args.target == tmp_path.resolve()
    assert args.ignore == [ArchiveType.CBR, ArchiveType.PDF]


def test_ignore_rejects_unknown_extensions(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["clean", "-i", "zip", str(tmp_path)])


def test_collect_files_skips_ignored_extensions(tmp_path: Path) -> None:
    for name in ("a.cbz", "b.cbr", "c.pdf"):
        (tmp_path / name).touch()
    args = build_parser().parse_args(["clean", "-i", "cbr", "-i", "PDF", str(tmp_path)])

    assert [x.name for x in collect_files(args)] == ["a.cbz"]


def test_collect_files_ignores_extensions_case_insensitively(tmp_path: Path) -> None:
    for name in ("a.cbz", "b.CBR", "c.Pdf"):
        (tmp_path / name).touch()
    args = build_parser().parse_args(["clean", "-i", "cbr", "-i", "PDF", str(tmp_path)])

    assert [x.name for x in collect_files(args)] == ["a.cbz"]


@pytest.mark.parametrize("command", ["sync", "pipeline"])
def test_sync_arguments_are_shared(command: str, tmp_path: Path) -> None:
    default = build_parser().parse_args([command, str(tmp_path)])
    flagged = build_parser().parse_args([command, "-f", "-o", str(tmp_path)])

    assert (default.force, default.override_cv_format) == (False, False)
    assert (flagged.force, flagged.override_cv_format) == (True, True)


@pytest.mark.parametrize("command", ["rename", "pipeline"])
def test_rename_arguments_are_shared(command: str, tmp_path: Path) -> None:
    default = build_parser().parse_args([command, str(tmp_path)])
    flagged = build_parser().parse_args([command, "--clean-empty", str(tmp_path)])

    assert default.clean_empty is False
    assert flagged.clean_empty is True


@pytest.mark.parametrize("flag", ["-f", "-o"])
def test_commands_without_sync_arguments_reject_them(flag: str, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["rename", flag, str(tmp_path)])


@pytest.mark.parametrize(
    "command", [["clean"], ["convert", "archive"], ["convert", "images"]], ids=" ".join
)
def test_dry_run_is_available(command: list[str], tmp_path: Path) -> None:
    default = build_parser().parse_args([*command, str(tmp_path)])
    flagged = build_parser().parse_args([*command, "--dry-run", str(tmp_path)])

    assert default.dry_run is False
    assert flagged.dry_run is True


def test_dry_run_is_not_available_in_the_pipeline(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["pipeline", "--dry-run", str(tmp_path)])


def test_pipeline_never_runs_dry(tmp_path: Path) -> None:
    assert build_parser().parse_args(["pipeline", str(tmp_path)]).dry_run is False


@pytest.mark.parametrize("command", ["rename", "sync"])
def test_dry_run_is_not_added_to_other_commands(command: str, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([command, "--dry-run", str(tmp_path)])
