__all__ = ["register"]

from argparse import _SubParsersAction

from rich.tree import Tree
from rich_argparse import HelpPreviewAction
from shortbox import Comic

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("tree", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument("target", type=existing_file, help="Comic to view details of.")
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_archive_tree.svg"
    )
    parser.set_defaults(func=run)


def run(args) -> None:  # noqa: ANN001
    with Comic.open(args.target) as comic:
        tree = Tree(comic.file.stem)
        for filename in comic.list_filenames():
            tree.add(filename)
        CONSOLE.print(tree)
