__all__ = ["register"]

from argparse import _SubParsersAction

from perdoo.cli._utils import add_command
from perdoo.cli.convert.archive import register as register_archive
from perdoo.cli.convert.images import register as register_images


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="convert",
        summary="Convert comic archives or the images inside them.",
        description="Convert comic archives or the images inside them, one at a time.",
    )
    subparsers = parser.add_subparsers(dest="convert-command", required=True)

    register_archive(subparsers=subparsers)
    register_images(subparsers=subparsers)
