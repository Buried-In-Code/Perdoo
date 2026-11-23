__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from pathlib import Path

from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.archives import Archive, TarArchive, ZipArchive

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Settings


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


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Converting '{args.target}'", style="title")
    settings = settings or Settings.load().save()
    target_format = determine_format(format_=settings.output.format)

    def handle(entry: Path) -> Outcome:
        with Comic.open(file=entry) as comic:
            original_file = comic.file
            new_file = comic.convert(
                archive_type=target_format, delete_original=True, raise_on_existing=False
            )
            return Outcome.UNCHANGED if new_file == original_file else Outcome.SUCCESS

    run_on_files(
        files=collect_files(args), action="Converting", handler=handle, capability_hint=None
    )
