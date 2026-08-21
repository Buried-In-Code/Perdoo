__all__ = ["register"]

from argparse import _SubParsersAction
from datetime import datetime
from enum import Enum

from comic_archive import Comic
from comic_archive.archives import Archive, PdfArchive, SevenZipArchive, TarArchive, ZipArchive
from comic_archive.metadata import ComicInfo, Metadata, MetronInfo
from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.services import BaseService, Comicvine, Metron
from perdoo.settings import Service, Services, Settings
from perdoo.utils import list_files


class SyncOption(str, Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"

    def __str__(self) -> str:
        return self.value


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "process",
        help="Process comics by converting, syncing metadata, and organizing them.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Process comics from the specified file/directory.",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip converting comics to the configured format.",
    )
    parser.add_argument(
        "-s",
        "--sync",
        type=enum_arg(enum_type=SyncOption),
        choices=list(SyncOption),
        default=SyncOption.OUTDATED,
        metavar="SYNC",
        help="Sync Metadata with online services.",
    )
    parser.add_argument(
        "--skip-clean", action="store_true", help="Skip removing any non-image/Metadata files."
    )
    parser.add_argument(
        "--skip-rename",
        action="store_true",
        help="Skip organizing and renaming comics based on their Metadata.",
    )
    parser.add_argument("-c", "--clean", action="store_true", help="Remove all cached files.")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode to show extra information."
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_process.svg"
    )
    parser.set_defaults(func=run)


def load_services(settings: Services) -> dict[Service, BaseService]:
    output = {}
    if settings.comicvine.api_key:
        output[Service.COMICVINE] = Comicvine(api_key=settings.comicvine.api_key)
    if settings.metron.token:
        output[Service.METRON] = Metron(token=settings.metron.token)
    return output


def determine_format(format_: str) -> type[Archive]:
    formats = {
        ZipArchive.extension: ZipArchive,
        TarArchive.extension: TarArchive,
        SevenZipArchive.extension: SevenZipArchive,
        PdfArchive.extension: PdfArchive,
    }
    return formats.get(f".{format_}", ZipArchive)


def convert_comic(comic: Comic, target_format: type[Archive]) -> None:
    if not isinstance(comic._archive, target_format):  # noqa: SLF001
        CONSOLE.print(f"Converting {comic.file.stem!r} to a {target_format.extension!r}")
        comic.convert(archive_type=target_format, delete_original=True)


def should_sync_metadata(sync: SyncOption, metron_info: MetronInfo | None) -> bool:
    if sync is SyncOption.SKIP:
        return False
    if sync is SyncOption.FORCE:
        return True
    if metron_info and metron_info.last_modified:
        age = (datetime.now().astimezone().date() - metron_info.last_modified.date()).days
        return age >= 28
    return True


def resolve_metadata(comic: Comic, sync: SyncOption) -> tuple[Metadata | None, ...]:
    comic_info = comic.get_metadata(metadata_type=ComicInfo)
    metron_info = comic.get_metadata(metadata_type=MetronInfo)
    if should_sync_metadata(sync=sync, metron_info=metron_info):
        return sync_metadata(
            service_order=service_order, services=services, metadata=(comic_info, metron_info)
        )
    return comic_info, metron_info


def run(args) -> None:  # noqa: ANN001
    settings = Settings.load().save()
    load_services(settings=settings.services)

    target_format = determine_format(format_=settings.output.format)
    files = list_files(args.target) if args.target.is_dir() else [args.target]

    _total = len(files)
    for _idx, entry in enumerate(files, start=1):
        with Comic.open(file=entry) as comic:
            if not args.skip_convert:
                convert_comic(comic=comic, target_format=target_format)
            comic_info, metron_info = resolve_metadata(comic=comic, sync=args.sync)
            if comic_info is None:
                comic.remove_metadata(ComicInfo)
            else:
                comic.set_metadata(comic_info)
            if metron_info is None:
                comic.remove_metadata(MetronInfo)
            else:
                comic.set_metadata(metron_info)
