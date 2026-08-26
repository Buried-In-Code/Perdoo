__all__ = ["register"]

from argparse import _SubParsersAction

from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import RichHelpFormatter
from perdoo.cli.archive.metadata import register_comic_info, register_metron_info


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("archive", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_archive.svg"
    )
    subparsers = parser.add_subparsers(dest="archive-command", required=True)

    register_comic_info(subparsers=subparsers)
    register_metron_info(subparsers=subparsers)
