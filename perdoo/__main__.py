import logging
from datetime import date
from enum import Enum
from pathlib import Path
from platform import python_version
from typing import Annotated

from comicfn2dict import comicfn2dict
from typer import Argument, Context, Exit, Option, Typer

from perdoo import __version__, get_cache_root, setup_logging
from perdoo.cli import archive_app, settings_app
from perdoo.comic import Comic
from perdoo.comic.errors import ComicArchiveError, ComicMetadataError
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.metron_info import Id, InformationSource
from perdoo.console import CONSOLE
from perdoo.processing import ProcessingPlan
from perdoo.services import BaseService, Comicvine, Metron
from perdoo.settings import Service, Services, Settings
from perdoo.utils import (
    IssueSearch,
    Search,
    SeriesSearch,
    delete_empty_folders,
    list_files,
    recursive_delete,
)

app = Typer(help="CLI tool for managing comic collections and settings.")
app.add_typer(archive_app, name="archive")
app.add_typer(settings_app, name="settings")
LOGGER = logging.getLogger("perdoo")


class SyncOption(Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"

    @staticmethod
    def load(value: str) -> "SyncOption":
        for entry in SyncOption:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"'{value}' isn't a valid SyncOption")


@app.callback(invoke_without_command=True)
def common(
    ctx: Context,
    version: Annotated[
        bool | None, Option("--version", is_eager=True, help="Show the version and exit.")
    ] = None,
) -> None:
    if ctx.invoked_subcommand:
        return
    if version:
        CONSOLE.print(f"Perdoo v{__version__}")
        raise Exit


def get_services(settings: Services) -> dict[Service, BaseService]:
    output = {}
    if settings.comicvine.api_key:
        output[Service.COMICVINE] = Comicvine(settings.comicvine)
    if settings.metron.username and settings.metron.password:
        output[Service.METRON] = Metron(settings.metron)
    return output


def setup_environment(
    clean_cache: bool, sync: SyncOption, settings: Settings, debug: bool = False
) -> tuple[dict[Service, BaseService], SyncOption]:
    setup_logging(debug=debug)
    LOGGER.info("Python v%s", python_version())
    LOGGER.info("Perdoo v%s", __version__)

    if clean_cache:
        LOGGER.info("Cleaning Cache")
        recursive_delete(path=get_cache_root())

    services = get_services(settings=settings.services)
    if not services and sync != SyncOption.SKIP:
        LOGGER.warning("No external services configured")
        sync = SyncOption.SKIP
    return services, sync


def load_comics(target: Path) -> list[Comic]:
    comics = []
    files = list_files(target) if target.is_dir() else [target]
    for file in files:
        try:
            comics.append(Comic(filepath=file))
        except (ComicArchiveError, ComicMetadataError) as err:  # noqa: PERF203
            LOGGER.error("Failed to load '%s' as a Comic: %s", file, err)
    return comics


def prepare_comic(entry: Comic, settings: Settings, skip_convert: bool) -> bool:
    if not skip_convert:
        entry.convert_to(settings.output.format)
    if not entry.archive.IS_WRITEABLE:
        LOGGER.warning("Archive format %s is not writeable", entry.archive.EXTENSION)
        return False
    return True


def should_sync_metadata(sync: SyncOption, metroninfo: MetronInfo | None) -> bool:
    if sync == SyncOption.SKIP:
        return False
    if sync == SyncOption.FORCE:
        return True
    if metroninfo and metroninfo.last_modified:
        age = (date.today() - metroninfo.last_modified.date()).days
        return age >= 28
    return True


def _get_id_value(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source == source), None)


def _create_search_from_metron_info(metron_info: MetronInfo) -> Search:
    series_id = metron_info.series.id
    source = next((x.source for x in metron_info.ids if x.primary), None)
    return Search(
        series=SeriesSearch(
            name=metron_info.series.name,
            volume=metron_info.series.volume,
            year=metron_info.series.start_year,
            comicvine=series_id if source == InformationSource.COMIC_VINE else None,
            metron=series_id if source == InformationSource.METRON else None,
        ),
        issue=IssueSearch(
            number=metron_info.number,
            comicvine=_get_id_value(metron_info.ids, InformationSource.COMIC_VINE),
            metron=_get_id_value(metron_info.ids, InformationSource.METRON),
        ),
    )


def _create_search_from_comic_info(comic_info: ComicInfo, filename: str) -> Search:
    volume = comic_info.volume if comic_info.volume else None
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=comic_info.series or filename, volume=volume, year=year),
        issue=IssueSearch(number=comic_info.number),
    )


def _create_search_from_filename(filename: str) -> Search:
    series_name = comicfn2dict(filename).get("series", filename).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch())


def get_search_details(
    metadata: tuple[MetronInfo | None, ComicInfo | None], filename: str
) -> Search:
    metron_info, comic_info = metadata
    if metron_info and metron_info.series and metron_info.series.name:
        return _create_search_from_metron_info(metron_info=metron_info)
    if comic_info and comic_info.series:
        return _create_search_from_comic_info(comic_info=comic_info, filename=filename)
    return _create_search_from_filename(filename=filename)


def sync_metadata(
    search: Search, services: dict[Service, BaseService | None], settings: Settings
) -> tuple[MetronInfo | None, ComicInfo | None]:
    for service_name in settings.services.order:
        if service := services.get(service_name):
            metron_info, comic_info = service.fetch(search=search)
            if metron_info or comic_info:
                return metron_info, comic_info
    return None, None


def resolve_metadata(
    entry: Comic, services: dict[Service, BaseService], settings: Settings, sync: SyncOption
) -> tuple[MetronInfo | None, ComicInfo | None]:
    metroninfo, comicinfo = entry.read_metadata()
    if not should_sync_metadata(sync=sync, metroninfo=metroninfo):
        return metroninfo, comicinfo
    search = get_search_details(metadata=(metroninfo, comicinfo), filename=entry.filepath.stem)
    search.filename = entry.filepath.stem
    return sync_metadata(search=search, services=services, settings=settings)


@app.command(name="import", help="Import comics into your collection using Perdoo.")
def run(
    target: Annotated[
        Path,
        Argument(
            exists=True, help="Import comics from the specified file/folder.", show_default=False
        ),
    ],
    skip_convert: Annotated[
        bool, Option("--skip-convert", help="Skip converting comics to the configured format.")
    ] = False,
    sync: Annotated[
        SyncOption,
        Option(
            "--sync",
            "-s",
            case_sensitive=False,
            help="Sync ComicInfo/MetronInfo with online services.",
        ),
    ] = SyncOption.OUTDATED,
    skip_clean: Annotated[
        bool,
        Option(
            "--skip-clean",
            help="Skip removing any files not listed in the 'image_extensions' setting.",
        ),
    ] = False,
    skip_rename: Annotated[
        bool,
        Option(
            "--skip-rename",
            help="Skip organizing and renaming comics based on their MetronInfo/ComicInfo.",
        ),
    ] = False,
    clean_cache: Annotated[
        bool,
        Option(
            "--clean",
            "-c",
            show_default=False,
            help="Clean the cache before starting the synchronization process. "
            "Removes all cached files.",
        ),
    ] = False,
    debug: Annotated[
        bool, Option("--debug", help="Enable debug mode to show extra information.")
    ] = False,
) -> None:
    settings = Settings.load()
    settings.save()
    services, sync = setup_environment(
        clean_cache=clean_cache, sync=sync, settings=settings, debug=debug
    )

    comics = load_comics(target=target)
    for index, entry in enumerate(comics):
        CONSOLE.rule(
            f"[{index + 1}/{len(comics)}] Importing {entry.filepath.name}",
            align="left",
            style="subtitle",
        )

        if not prepare_comic(entry=entry, settings=settings, skip_convert=skip_convert):
            continue
        metroninfo, comicinfo = resolve_metadata(
            entry=entry, services=services, settings=settings, sync=sync
        )
        plan = ProcessingPlan.build(
            entry=entry,
            metroninfo=metroninfo,
            comicinfo=comicinfo,
            settings=settings.output,
            skip_clean=skip_clean,
            skip_rename=skip_rename,
        )
        plan.apply()
        if plan.naming:
            entry.move_to(naming=plan.naming, output_folder=settings.output.folder)
    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


if __name__ == "__main__":
    app(prog_name="Perdoo")
