__all__ = ["register"]

from argparse import _SubParsersAction

from perdoo.cli._utils import add_command
from perdoo.cli.archive.metadata import register as register_metadata
from perdoo.cli.archive.remove import register as register_remove
from perdoo.cli.archive.tree import register as register_tree


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="archive",
        summary="Inspect the contents and metadata of comic archives.",
        description="Inspect the contents and metadata of a comic archive.",
    )
    subparsers = parser.add_subparsers(dest="archive-command", required=True)

    register_metadata(subparsers=subparsers)
    register_remove(subparsers=subparsers)
    register_tree(subparsers=subparsers)
