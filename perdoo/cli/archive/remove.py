__all__ = ["register"]

from argparse import _SubParsersAction

from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import MissingArchiveMemberError

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("remove", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument("target", type=existing_file, help="Comic to view details of.")
    parser.add_argument("entry", type=str, help="TODO")
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path="docs/img/perdoo_archive_remove.svg",
    )
    parser.set_defaults(func=run)


def run(args) -> None:  # noqa: ANN001
    with Comic.open(args.target) as comic:
        try:
            comic.remove_file(args.entry)
        except MissingArchiveMemberError as err:
            CONSOLE.print(err, style="logging.level.error")
