__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from perdoo.cli._utils import add_command
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="settings",
        summary="Display current settings and default values.",
        description="Display the configured settings alongside their default values.",
    )
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:  # noqa: ARG001
    Settings.display()
