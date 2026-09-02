__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich.tree import Tree
from rich_argparse import HelpPreviewAction
from shortbox import Comic

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "tree",
        help="List entries in a comic archive as a tree.",
        description="List the entries in a comic archive as a tree.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("target", type=existing_file, help="Comic archive whose entries to list.")
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_archive_tree.svg"
    )
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:
    with Comic.open(args.target) as comic:
        tree = Tree(comic.file.stem)
        for filename in comic.list_filenames():
            tree.add(filename)
        CONSOLE.print(tree)
