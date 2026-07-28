__all__ = ["RichHelpFormatter"]

from argparse import (
    SUPPRESS,
    Action,
    ArgumentDefaultsHelpFormatter,
    BooleanOptionalAction,
    _StoreFalseAction,
    _StoreTrueAction,
)

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
