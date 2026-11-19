__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from rich_argparse import HelpPreviewAction
from shortbox import Comic

from perdoo.cli._runner import Outcome, RunSummary, collect_files, run_on_files
from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "clean",
        help="Remove configured unwanted files from comic archives.",
        description="Remove files with extensions configured in output.remove-extensions from comic archives.",  # noqa: E501
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Comic archive or directory of comic archives to clean.",
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
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_clean.svg"
    )
    parser.set_defaults(func=run)


def clean_comic(comic: Comic, remove_extensions: Sequence[str]) -> Outcome:
    removed = [name for name in comic.list_filenames() if Path(name).suffix in remove_extensions]
    for filename in removed:
        CONSOLE.print(f"Removing {filename!r}")
        comic.remove_file(filename=filename)
    return Outcome.SUCCESS if removed else Outcome.UNCHANGED


def run(args: Namespace) -> RunSummary:
    settings = Settings.load().save()

    def handle(entry: Path) -> Outcome:
        with Comic.open(file=entry) as comic:
            return clean_comic(comic=comic, remove_extensions=settings.output.remove_extensions)

    return run_on_files(files=collect_files(args), action="Cleaning", handler=handle)
