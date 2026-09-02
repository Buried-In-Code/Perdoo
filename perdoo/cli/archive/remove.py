__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import MissingArchiveMemberError

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "remove",
        help="Remove an entry from a comic archive.",
        description="Remove a file or directory entry from a comic archive.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target", type=existing_file, help="Comic archive from which to remove an entry."
    )
    parser.add_argument("entry", type=str, help="Exact path of the archive entry to remove.")
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path="docs/img/perdoo_archive_remove.svg",
    )
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:
    with Comic.open(args.target) as comic:
        try:
            comic.remove_file(args.entry)
        except MissingArchiveMemberError as err:
            CONSOLE.print(err, style="logging.level.error")
