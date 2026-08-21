__all__ = ["RichHelpFormatter", "enum_arg", "existing_file", "existing_file_or_directory"]

from argparse import (
    SUPPRESS,
    Action,
    ArgumentDefaultsHelpFormatter,
    ArgumentTypeError,
    BooleanOptionalAction,
    _StoreFalseAction,
    _StoreTrueAction,
)
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from rich_argparse import RichHelpFormatter as _RichHelpFormatter

_FLAG_ACTIONS = (_StoreTrueAction, _StoreFalseAction, BooleanOptionalAction)


class RichHelpFormatter(ArgumentDefaultsHelpFormatter, _RichHelpFormatter):
    def _get_help_string(self, action: Action) -> str | None:
        help_text = ""
        choices = ""
        default = ""
        if action.help:
            help_text = action.help
        if action.choices:
            choices = " [yellow][" + ("|".join(map(str, action.choices))) + "][/]"
        if (
            action.default is not None
            and action.default != SUPPRESS
            and not isinstance(action, _FLAG_ACTIONS)
        ):
            default = f" [dim][Default: {action.default}][/]"
        return help_text + choices + default


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ArgumentTypeError(f"target path is not a file: {value!r}")
    if not path.exists():
        raise ArgumentTypeError(f"target file must exist: {value!r}")
    return path


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
