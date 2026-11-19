__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Mapping
from pathlib import Path

from rich.table import Table
from rich_argparse import HelpPreviewAction

from perdoo.cli._runner import RunSummary
from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.cli.clean import run as run_clean
from perdoo.cli.convert import run as run_convert
from perdoo.cli.rename import run as run_rename
from perdoo.cli.sync import run as run_sync
from perdoo.console import CONSOLE, Grid


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "pipeline",
        help="Runs convert, clean, sync and rename one after another",
        description="Runs convert, clean, sync and rename one after another",
        formatter_class=RichHelpFormatter,
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
        "-o",
        "--override-cv-format",
        action="store_true",
        help="Override the format provided by Comicvine",
    )
    parser.add_argument(
        "-c",
        "--clean-empty",
        action="store_true",
        help="Remove any empty folders after processing inside the target, including the target",
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_pipeline.svg"
    )
    parser.set_defaults(func=run)


def delete_empty_folders(root: Path, folder: Path) -> None:
    if folder.is_dir():
        for subfolder in folder.iterdir():
            if subfolder.is_dir():
                delete_empty_folders(root=root, folder=subfolder)
        if not any(folder.iterdir()):
            folder.rmdir()
            relative = folder.relative_to(root)
            CONSOLE.print(f"Deleted empty folder: '{relative}'")


def build_pipeline_summary(stages: Mapping[str, RunSummary]) -> Table:
    table = Grid(title="Pipeline Summary")
    for name, summary in stages.items():
        table.add_row(name, summary.status.value)
    return table


def run(args: Namespace) -> None:
    stages = {
        "Convert": run_convert(args),
        "Clean": run_clean(args),
        "Sync": run_sync(args),
        "Rename": run_rename(args),
    }
    if args.clean_empty:
        with CONSOLE.status("Cleaning up empty folders"):
            delete_empty_folders(root=args.target, folder=args.target)
    CONSOLE.print(build_pipeline_summary(stages))
