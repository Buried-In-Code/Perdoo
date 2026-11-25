__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich.tree import Tree
from shortbox import Comic

from perdoo.cli._utils import add_command, existing_file
from perdoo.console import CONSOLE


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="tree",
        summary="List entries in a comic archive as a tree.",
        description="List the entries in a comic archive as a tree.",
    )
    parser.add_argument("target", type=existing_file, help="Comic archive whose entries to list.")
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:
    with Comic.open(args.target) as comic:
        tree = Tree(comic.file.stem)
        for filename in comic.list_filenames():
            tree.add(filename)
        CONSOLE.print(tree)
