__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from perdoo.cli._utils import (
    add_command,
    add_rename_arguments,
    add_sync_arguments,
    add_target_arguments,
)
from perdoo.cli.clean import run as run_clean
from perdoo.cli.convert.archive import run as run_convert_archive
from perdoo.cli.convert.images import run as run_convert_images
from perdoo.cli.rename import run as run_rename
from perdoo.cli.sync import run as run_sync
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="pipeline",
        summary="Runs convert (archives & images), clean, sync and rename in order",
        description="Runs convert (archives & images), clean, sync and rename in order",
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to process"
    )
    add_sync_arguments(parser=parser)
    add_rename_arguments(parser=parser)
    parser.set_defaults(func=run, dry_run=False)


def run(args: Namespace) -> None:
    settings = Settings.load().save()
    run_convert_archive(args, settings)
    run_convert_images(args, settings)
    run_clean(args, settings)
    run_sync(args, settings)
    run_rename(args, settings)
