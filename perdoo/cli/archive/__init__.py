__all__ = ["register"]

from argparse import _SubParsersAction

from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import RichHelpFormatter
from perdoo.cli.archive.metadata import register as register_metadata
from perdoo.cli.archive.remove import register as register_remove
from perdoo.cli.archive.tree import register as register_tree


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "archive",
        help="Inspect the contents and metadata of comic archives.",
        description="Inspect the contents and metadata of a comic archive.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_archive.svg"
    )
    subparsers = parser.add_subparsers(dest="archive-command", required=True)

    register_metadata(subparsers=subparsers)
    register_remove(subparsers=subparsers)
    register_tree(subparsers=subparsers)
