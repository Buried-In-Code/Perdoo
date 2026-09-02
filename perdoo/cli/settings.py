__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import RichHelpFormatter
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "settings",
        help="Display current settings and default values.",
        description="Display the configured settings alongside their default values.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_settings.svg"
    )
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:  # noqa: ARG001
    Settings.display()
