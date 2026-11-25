__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from shortbox import Comic
from shortbox.errors import MetadataValidationError
from shortbox.metadata import ComicInfo, MetronInfo

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import add_command, add_sync_arguments, add_target_arguments
from perdoo.console import CONSOLE
from perdoo.services import Fetcher, build_fetchers, build_query
from perdoo.services._models import get_comic_info_note_modified
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="sync",
        summary="Fetch metadata for comic archives from configured services.",
        description="Fetch metadata from configured services and store it in comic archives.",
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to sync"
    )
    add_sync_arguments(parser=parser)
    parser.set_defaults(func=run)


def should_sync(metron_info: MetronInfo | None, comic_info: ComicInfo | None, days: int) -> bool:
    last_modified = metron_info.last_modified if metron_info else None
    last_modified = last_modified or get_comic_info_note_modified(
        comic_info.notes if comic_info else None
    )
    if last_modified:
        age = (datetime.now().astimezone().date() - last_modified.date()).days
        return age >= days
    return True


def sync_comic(
    comic: Comic, fetchers: Sequence[Fetcher], days: int, force: bool = False
) -> Outcome:
    try:
        metron_info = comic.get_metadata(MetronInfo)
    except MetadataValidationError as err:
        CONSOLE.print(str(err), style="logging.level.error")
        metron_info = None
    try:
        comic_info = comic.get_metadata(ComicInfo)
    except MetadataValidationError as err:
        CONSOLE.print(str(err), style="logging.level.error")
        comic_info = None
    if not should_sync(metron_info=metron_info, comic_info=comic_info, days=days) and not force:
        return Outcome.UNCHANGED
    query = build_query(comic=comic)
    for fetcher in fetchers:
        if result := fetcher.fetch(query):
            with CONSOLE.status("Writing ComicInfo.xml to archive"):
                comic.set_metadata(result.comic_info)
            with CONSOLE.status("Writing MetronInfo.xml to archive"):
                comic.set_metadata(result.metron_info)
            return Outcome.SUCCESS
    CONSOLE.print(f"No metadata found for '{comic.file.name}'", style="logging.level.warning")
    return Outcome.FAILED


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Syncing '{args.target}'", style="title")
    settings = settings or Settings.load().save()
    fetchers = build_fetchers(settings, ask_format=args.override_cv_format)
    if not fetchers:
        CONSOLE.print("No services configured", style="logging.level.error")
        return

    def handle(entry: Path) -> Outcome:
        with Comic.open(file=entry) as comic:
            return sync_comic(
                comic=comic, fetchers=fetchers, days=settings.sync.days, force=args.force
            )

    run_on_files(files=collect_files(args), action="Syncing", handler=handle, show_progress=False)
