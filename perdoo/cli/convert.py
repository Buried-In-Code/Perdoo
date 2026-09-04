__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.archives import Archive, TarArchive, ZipArchive
from shortbox.errors import UnsupportedArchiveError

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Settings
from perdoo.utils import list_files


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "convert",
        help="Convert comic archives to the configured output format.",
        description="Convert comic archives to the format configured in output.format.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Comic archive or directory of comic archives to convert.",
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
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_convert.svg"
    )
    parser.set_defaults(func=run)


def determine_format(format_: str) -> type[Archive]:
    formats: dict[str, type[Archive]] = {
        ZipArchive.extension: ZipArchive,
        TarArchive.extension: TarArchive,
    }
    from shortbox import archives  # noqa: PLC0415

    if sevenzip_archive := getattr(archives, "SevenZipArchive", None):
        formats[sevenzip_archive.extension] = sevenzip_archive
    if rar_archive := getattr(archives, "RarArchive", None):
        formats[rar_archive.extension] = rar_archive
    if pdf_archive := getattr(archives, "PdfArchive", None):
        formats[pdf_archive.extension] = pdf_archive
    output = formats.get(f".{format_}")
    if output is None:
        CONSOLE.print(
            f"{format_!r} output requires `perdoo[{format_}]`; install it and retry",
            style="logging.level.warning",
        )
        raise SystemExit(1)
    return output


def run(args: Namespace) -> None:
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
