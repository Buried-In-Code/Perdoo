__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from datetime import datetime

from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import ArchiveCapabilityError, UnsupportedArchiveError
from shortbox.metadata import ComicInfo, MetronInfo

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.services import Comicvine, Metron, Search, Service
from perdoo.services._models import get_comic_info_note_modified
from perdoo.settings import Service as ServiceOption, Services, Settings
from perdoo.utils import list_files


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "sync",
        help="Fetch metadata for comic archives from configured services.",
        description="Fetch metadata from configured services and store it in comic archives.",
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
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_sync.svg"
    )
    parser.set_defaults(func=run)


def build_services(services: Services, cover_hash_distance: int) -> Sequence[Service]:
    tmp = {}
    if services.comicvine.api_key:
        tmp[ServiceOption.COMICVINE] = Comicvine(api_key=services.comicvine.api_key)
    if services.metron.token:
        tmp[ServiceOption.METRON] = Metron(
            token=services.metron.token, cover_hash_distance=cover_hash_distance
        )
    return [tmp[k] for k in services.order if k in tmp]


def should_sync(metron_info: MetronInfo | None, comic_info: ComicInfo | None, days: int) -> bool:
    last_modified = metron_info.last_modified if metron_info else None
    last_modified = last_modified or get_comic_info_note_modified(
        comic_info.notes if comic_info else None
    )
    if last_modified:
        age = (datetime.now().astimezone().date() - last_modified.date()).days
        return age >= days
    return True


def sync_comic(comic: Comic, services: Sequence[Service], days: int, force: bool = False) -> None:
    if (
        not should_sync(
            metron_info=comic.get_metadata(MetronInfo),
            comic_info=comic.get_metadata(ComicInfo),
            days=days,
        )
        and not force
    ):
        return
    query = Search.build(comic=comic)
    try:
        for svc in services:
            if result := svc.fetch(search=query):
                comic.set_metadata(result.comic_info)
                comic.set_metadata(result.metron_info)
                break
    except ArchiveCapabilityError as err:
        CONSOLE.print(
            f"{err}: Consider converting to another format first", style="logging.level.warning"
        )


def run(args: Namespace) -> None:
    settings = Settings.load().save()
    services = build_services(
        services=settings.services, cover_hash_distance=settings.sync.cover_hash_distance
    )
    if not services:
        CONSOLE.print("No services configured", style="logging.level.error")
        return

    files = list_files(args.target) if args.target.is_dir() else [args.target]
    if args.ignore:
        ignore_ext = [f".{x}" for x in args.ignore]
        files = [x for x in files if x.suffix not in ignore_ext]

    for entry in files:
        try:
            with Comic.open(file=entry) as comic:
                sync_comic(
                    comic=comic, services=services, days=settings.sync.days, force=args.force
                )
        except UnsupportedArchiveError:  # noqa: PERF203
            pass
