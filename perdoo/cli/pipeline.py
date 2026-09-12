__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.cli.clean import run as run_clean
from perdoo.cli.convert import run as run_convert
from perdoo.cli.rename import run as run_rename
from perdoo.cli.sync import run as run_sync


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "pipeline", help="", description="", formatter_class=RichHelpFormatter
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Comic archive or directory of comic archives to synchronize.",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        type=enum_arg(enum_type=ArchiveType),
        choices=list(ArchiveType),
        metavar="EXT",
        help="Skip archives with this extension. Repeat to ignore multiple extensions.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Synchronize even if the stored metadata was updated within the configured interval.",
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_pipeline.svg"
    )
    parser.set_defaults(func=run)


def run(args: Namespace) -> None:
    run_convert(args)
    run_clean(args)
    run_sync(args)
    run_rename(args)
