__all__ = ["build_parser"]

from argparse import ArgumentParser

from perdoo import __project__, __version__
from perdoo.cli._utils import RichHelpFormatter, add_help_preview
from perdoo.cli.archive import register as register_archive
from perdoo.cli.clean import register as register_clean
from perdoo.cli.convert import register as register_convert
from perdoo.cli.pipeline import register as register_pipeline
from perdoo.cli.rename import register as register_rename
from perdoo.cli.settings import register as register_settings
from perdoo.cli.sync import register as register_sync


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog=__project__,
        description="Organize comic collections using metadata stored in comic archives.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{__version__}",
        help="Show the installed version and exit.",
    )
    add_help_preview(parser=parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_archive(subparsers=subparsers)
    register_clean(subparsers=subparsers)
    register_convert(subparsers=subparsers)
    register_pipeline(subparsers=subparsers)
    register_rename(subparsers=subparsers)
    register_settings(subparsers=subparsers)
    register_sync(subparsers=subparsers)

    return parser
