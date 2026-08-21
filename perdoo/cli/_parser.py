__all__ = ["build_parser"]

from argparse import ArgumentParser

from rich_argparse import HelpPreviewAction

from perdoo import __project__, __version__
from perdoo.cli._utils import RichHelpFormatter
from perdoo.cli.archive import register as register_archive
from perdoo.cli.process import register as register_process
from perdoo.cli.settings import register as register_settings


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog=__project__, formatter_class=RichHelpFormatter)
    parser.add_argument("--version", action="version", version=f"%(prog)s v{__version__}")
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo.svg"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_archive(subparsers=subparsers)
    register_process(subparsers=subparsers)
    register_settings(subparsers=subparsers)

    return parser
