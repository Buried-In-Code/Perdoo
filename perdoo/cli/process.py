__all__ = ["register"]

from argparse import ArgumentTypeError, _SubParsersAction
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from rich_argparse import HelpPreviewAction

from perdoo.cli._help import RichHelpFormatter


def existing_file_or_directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ArgumentTypeError(f"target file/directory must exist: {value!r}")
    return path


def enum_arg(enum_type: type[Enum]) -> Callable[[str], Enum]:
    def convert(value: str) -> Enum:
        value = value.lower()
        for member in enum_type:
            if (
                member.value.casefold() == value.casefold()
                or member.name.casefold() == value.casefold()
            ):
                return member
        raise ValueError(f"invalid choice: {value}")

    return convert


class SyncOption(str, Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"

    def __str__(self) -> str:
        return self.value


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "process",
        help="Process comics by converting, syncing metadata, and organizing them.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Process comics from the specified file/directory.",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip converting comics to the configured format.",
    )
    parser.add_argument(
        "-s",
        "--sync",
        type=enum_arg(enum_type=SyncOption),
        choices=list(SyncOption),
        default=SyncOption.OUTDATED,
        metavar="SYNC",
        help="Sync Metadata with online services.",
    )
    parser.add_argument(
        "--skip-clean", action="store_true", help="Skip removing any non-image/Metadata files."
    )
    parser.add_argument(
        "--skip-rename",
        action="store_true",
        help="Skip organizing and renaming comics based on their Metadata.",
    )
    parser.add_argument("-c", "--clean", action="store_true", help="Remove all cached files.")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode to show extra information."
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_process.svg"
    )
    parser.set_defaults(func=run)


def run(args) -> None:  # noqa: ANN001
    pass
