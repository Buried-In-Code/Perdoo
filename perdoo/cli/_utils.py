__all__ = [
    "RichHelpFormatter",
    "add_command",
    "add_dry_run_argument",
    "add_help_preview",
    "add_rename_arguments",
    "add_sync_arguments",
    "add_target_arguments",
    "existing_file",
    "existing_file_or_directory",
]

from argparse import (
    SUPPRESS,
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    ArgumentTypeError,
    BooleanOptionalAction,
    _StoreFalseAction,
    _StoreTrueAction,
    _SubParsersAction,
)
from pathlib import Path

from rich.markup import escape
from rich_argparse import HelpPreviewAction, RichHelpFormatter as _RichHelpFormatter

from perdoo.formats import ArchiveType

_FLAG_ACTIONS = (_StoreTrueAction, _StoreFalseAction, BooleanOptionalAction)


class RichHelpFormatter(ArgumentDefaultsHelpFormatter, _RichHelpFormatter):
    def _get_help_string(self, action: Action) -> str | None:
        help_text = ""
        choices = ""
        default = ""
        if action.help:
            help_text = action.help
        if action.choices:
            choices_str = escape("[" + ("|".join(map(str, action.choices))) + "]")
            choices = f" [yellow]{choices_str}[/]"
        if (
            action.default is not None
            and action.default != SUPPRESS
            and not isinstance(action, _FLAG_ACTIONS)
        ):
            default_str = escape(f"[Default: {action.default}]")
            default = f" [dim]{default_str}[/]"
        return help_text + choices + default


def add_help_preview(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path=f"docs/img/{parser.prog.replace(' ', '_')}.svg",
    )


def add_command(
    subparsers: _SubParsersAction, name: str, summary: str, description: str
) -> ArgumentParser:
    parser = subparsers.add_parser(
        name, help=summary, description=description, formatter_class=RichHelpFormatter
    )
    add_help_preview(parser=parser)
    return parser


def add_target_arguments(parser: ArgumentParser, target_help: str) -> None:
    parser.add_argument("target", type=existing_file_or_directory, help=target_help)
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        type=ArchiveType,
        choices=list(ArchiveType),
        metavar="EXT",
        help="Skip archives with this extension. Repeat to ignore multiple extensions.",
    )


def add_dry_run_argument(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run", action="store_true", help="Log what would change without changing anything."
    )


def add_sync_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Synchronize even if the stored metadata was updated within the configured interval.",
    )
    parser.add_argument(
        "-o",
        "--override-cv-format",
        action="store_true",
        help="Override the format provided by Comicvine",
    )


def add_rename_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-c",
        "--clean-empty",
        action="store_true",
        help="Remove any empty folders after processing inside the target, including the target",
    )


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ArgumentTypeError(f"target file must exist: {value!r}")
    if not path.is_file():
        raise ArgumentTypeError(f"target path is not a file: {value!r}")
    return path


def existing_file_or_directory(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ArgumentTypeError(f"target file/directory must exist: {value!r}")
    if not path.is_file() and not path.is_dir():
        raise ArgumentTypeError(f"target path is not a file/directory: {value!r}")
    return path
