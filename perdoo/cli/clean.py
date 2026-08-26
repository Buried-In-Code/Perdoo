__all__ = ["register"]

from argparse import _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from comic_archive import Comic
from comic_archive.errors import ArchiveCapabilityError, UnsupportedArchiveError
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Settings
from perdoo.utils import list_files


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("clean", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Process comics from the specified file/directory.",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        type=enum_arg(enum_type=ArchiveType),
        choices=list(ArchiveType),
        metavar="ARCHIVE",
        help="TODO",
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_clean.svg"
    )
    parser.set_defaults(func=run)


def clean_comic(comic: Comic, remove_exts: Sequence[str]) -> None:
    try:
        for filename in comic.list_filenames():
            if Path(filename).suffix in remove_exts:
                CONSOLE.print(f"Removing {filename!r}")
                comic.remove_file(filename=filename)
    except ArchiveCapabilityError as err:
        CONSOLE.print(
            f"{err}: Consider converting to another format first", style="logging.level.warning"
        )


def run(args) -> None:  # noqa: ANN001
    settings = Settings.load().save()

    files = list_files(args.target) if args.target.is_dir() else [args.target]
    if args.ignore:
        ignore_ext = [f".{x}" for x in args.ignore]
        files = [x for x in files if x.suffix not in ignore_ext]
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=CONSOLE,
        expand=True,
    )

    with progress:
        for entry in progress.track(files, description="Cleaning comics"):
            try:
                with Comic.open(file=entry) as comic:
                    clean_comic(comic=comic, remove_exts=settings.output.remove_extensions)
            except UnsupportedArchiveError:  # noqa: PERF203
                pass
