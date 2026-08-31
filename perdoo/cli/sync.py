__all__ = ["register"]

from argparse import _SubParsersAction
from collections.abc import Sequence
from datetime import datetime

from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import ArchiveCapabilityError, UnsupportedArchiveError
from shortbox.metadata import MetronInfo

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.services import Comicvine, Metron, Search, Service
from perdoo.settings import Service as ServiceOption, Services, Settings
from perdoo.utils import list_files


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("sync", help="TODO", formatter_class=RichHelpFormatter)
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
    parser.add_argument("-f", "--force", action="store_true", help="TODO")
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_sync.svg"
    )
    parser.set_defaults(func=run)


def build_services(settings: Services) -> Sequence[Service]:
    tmp = {}
    if settings.comicvine.api_key:
        tmp[ServiceOption.COMICVINE] = Comicvine(api_key=settings.comicvine.api_key)
    if settings.metron.token:
        tmp[ServiceOption.METRON] = Metron(token=settings.metron.token)
    return [tmp[k] for k in settings.order if k in tmp]


def should_sync(metron_info: MetronInfo | None) -> bool:
    if metron_info and metron_info.last_modified:
        age = (datetime.now().astimezone().date() - metron_info.last_modified.date()).days
        return age >= 28
    return True


def sync_comic(comic: Comic, services: Sequence[Service], force: bool = False) -> None:
    if not should_sync(metron_info=comic.get_metadata(MetronInfo)) and not force:
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


def run(args) -> None:  # noqa: ANN001
    settings = Settings.load().save()
    services = build_services(settings=settings.services)
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
                sync_comic(comic=comic, services=services, force=args.force)
        except UnsupportedArchiveError:  # noqa: PERF203
            pass
