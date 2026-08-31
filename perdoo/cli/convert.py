__all__ = ["register"]

from argparse import _SubParsersAction

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.archives import Archive, PdfArchive, SevenZipArchive, TarArchive, ZipArchive
from shortbox.errors import UnsupportedArchiveError

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Settings
from perdoo.utils import list_files


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("convert", help="TODO", formatter_class=RichHelpFormatter)
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
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_convert.svg"
    )
    parser.set_defaults(func=run)


def determine_format(format_: str) -> type[Archive]:
    formats = {
        ZipArchive.extension: ZipArchive,
        TarArchive.extension: TarArchive,
        SevenZipArchive.extension: SevenZipArchive,
        PdfArchive.extension: PdfArchive,
    }
    return formats.get(f".{format_}", ZipArchive)


def run(args) -> None:  # noqa: ANN001
    settings = Settings.load().save()

    target_format = determine_format(format_=settings.output.format)
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
        for entry in progress.track(files, description="Converting comics"):
            try:
                with Comic.open(file=entry) as comic:
                    comic.convert(
                        archive_type=target_format, delete_original=True, raise_on_existing=False
                    )
            except UnsupportedArchiveError:  # noqa: PERF203
                pass
