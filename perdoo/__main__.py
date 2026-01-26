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
from perdoo.comic.archive import ArchiveSession
from perdoo.comic.errors import ComicArchiveError, ComicMetadataError
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.metron_info import Id, InformationSource
from perdoo.console import CONSOLE
from perdoo.services import BaseService, Comicvine, Metron
from perdoo.settings import Naming, Output, Service, Services, Settings
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


class SyncOption(str, Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"


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
    if not services and sync is not SyncOption.SKIP:
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


def should_sync_metadata(sync: SyncOption, metron_info: MetronInfo | None) -> bool:
    if sync is SyncOption.SKIP:
        return False
    if sync is SyncOption.FORCE:
        return True
    if metron_info and metron_info.last_modified:
        age = (date.today() - metron_info.last_modified.date()).days
        return age >= 28
    return True


def get_id(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source is source), None)


def search_from_metron_info(metron_info: MetronInfo) -> Search:
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
            comicvine=get_id(metron_info.ids, InformationSource.COMIC_VINE),
            metron=get_id(metron_info.ids, InformationSource.METRON),
        ),
    )


def search_from_comic_info(comic_info: ComicInfo, filename: str) -> Search:
    volume = comic_info.volume
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=comic_info.series or filename, volume=volume, year=year),
        issue=IssueSearch(number=comic_info.number),
    )


def search_from_filename(filename: str) -> Search:
    series_name = comicfn2dict(filename).get("series", filename).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch())


def build_search(
    metron_info: MetronInfo | None, comic_info: ComicInfo | None, filename: str
) -> Search:
    if metron_info and metron_info.series and metron_info.series.name:
        return search_from_metron_info(metron_info=metron_info)
    if comic_info and comic_info.series:
        return search_from_comic_info(comic_info=comic_info, filename=filename)
    return search_from_filename(filename=filename)


def sync_metadata(
    search: Search, services: dict[Service, BaseService], service_order: tuple[Service, ...]
) -> tuple[MetronInfo | None, ComicInfo | None]:
    for service_name in service_order:
        if service := services.get(service_name):
            metron_info, comic_info = service.fetch(search=search)
            if metron_info or comic_info:
                return metron_info, comic_info
    return None, None


def resolve_metadata(
    entry: Comic,
    session: ArchiveSession,
    services: dict[Service, BaseService],
    settings: Services,
    sync: SyncOption,
) -> tuple[MetronInfo | None, ComicInfo | None]:
    metron_info, comic_info = entry.read_metadata(session=session)
    if not should_sync_metadata(sync=sync, metron_info=metron_info):
        return metron_info, comic_info
    search = build_search(
        metron_info=metron_info, comic_info=comic_info, filename=entry.filepath.stem
    )
    search.filename = entry.filepath.stem
    return sync_metadata(search=search, services=services, service_order=settings.order)


def generate_naming(
    settings: Naming, metron_info: MetronInfo | None, comic_info: ComicInfo | None
) -> str | None:
    filepath = None
    if metron_info:
        filepath = metron_info.get_filename(settings=settings)
    if not filepath and comic_info:
        filepath = comic_info.get_filename(settings=settings)
    return filepath.lstrip("/") if filepath else None


def apply_changes(
    entry: Comic,
    session: ArchiveSession,
    metron_info: MetronInfo | None,
    comic_info: ComicInfo | None,
    skip_clean: bool,
    skip_rename: bool,
    settings: Output,
) -> str | None:
    local_metron_info, local_comic_info = entry.read_metadata(session=session)
    if local_metron_info != metron_info:
        if metron_info:
            session.write(filename=MetronInfo.FILENAME, data=metron_info.to_bytes())
        else:
            session.remove(filename=MetronInfo.FILENAME)
        session.updated = True

    if local_comic_info != comic_info:
        if comic_info:
            session.write(filename=ComicInfo.FILENAME, data=comic_info.to_bytes())
        else:
            session.remove(filename=ComicInfo.FILENAME)
        session.updated = True

    if not skip_clean:
        for extra in entry.list_extras():
            session.remove(filename=extra.name)
            session.updated = True

    naming = None
    if not skip_rename and (
        naming := generate_naming(
            settings=settings.naming, metron_info=metron_info, comic_info=comic_info
        )
    ):
        images = entry.list_images()
        stem = Path(naming).stem
        pad = len(str(len(images)))
        for idx, img in enumerate(images):
            new_name = f"{stem}_{str(idx).zfill(pad)}{img.suffix}"
            if img.name != new_name:
                session.rename(old_name=img.name, new_name=new_name)
                session.updated = True
    return naming


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
    total = len(comics)
    for index, entry in enumerate(comics, start=1):
        CONSOLE.rule(
            f"[{index}/{total}] Importing {entry.filepath.name}", align="left", style="subtitle"
        )

        if not prepare_comic(entry=entry, settings=settings, skip_convert=skip_convert):
            continue
        with entry.open_session() as session:
            metron_info, comic_info = resolve_metadata(
                entry=entry,
                session=session,
                services=services,
                settings=settings.services,
                sync=sync,
            )
            naming = apply_changes(
                entry=entry,
                session=session,
                metron_info=metron_info,
                comic_info=comic_info,
                skip_clean=skip_clean,
                skip_rename=skip_rename,
                settings=settings.output,
            )
        if naming:
            entry.move_to(naming=naming, output_folder=settings.output.folder)
    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


if __name__ == "__main__":
    app(prog_name="Perdoo")
