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
from perdoo.comic import SUPPORTED_IMAGE_EXTENSIONS, Comic, ComicArchiveError, ComicMetadataError
from perdoo.console import CONSOLE
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.comic_info import Page
from perdoo.metadata.metron_info import Id, InformationSource
from perdoo.services import BaseService, Comicvine, Marvel, Metron
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

    def __str__(self) -> str:
        return self.value


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
    if settings.marvel.public_key and settings.marvel.private_key:
        output[Service.MARVEL] = Marvel(settings.marvel)
    if settings.metron.username and settings.metron.password:
        output[Service.METRON] = Metron(settings.metron)
    return output


def _load_comics(target: Path) -> list[Comic]:
    comics = []
    files = list_files(target) if target.is_dir() else [target]
    for file in files:
        try:
            comics.append(Comic(file=file))
        except (ComicArchiveError, ComicMetadataError) as err:  # noqa: PERF203
            LOGGER.error("Failed to load '%s' as a Comic: %s", file, err)
    return comics


def _get_id_value(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source == source), None)


def _create_search_from_metron(metron_info: MetronInfo) -> Search:
    series_id = metron_info.series.id
    source = next((x.source for x in metron_info.ids if x.primary), None)
    return Search(
        series=SeriesSearch(
            name=metron_info.series.name,
            volume=metron_info.series.volume,
            year=metron_info.series.start_year,
            comicvine=series_id if source == InformationSource.COMIC_VINE else None,
            marvel=series_id if source == InformationSource.MARVEL else None,
            metron=series_id if source == InformationSource.METRON else None,
        ),
        issue=IssueSearch(
            number=metron_info.number,
            comicvine=_get_id_value(metron_info.ids, InformationSource.COMIC_VINE),
            marvel=_get_id_value(metron_info.ids, InformationSource.MARVEL),
            metron=_get_id_value(metron_info.ids, InformationSource.METRON),
        ),
    )


def _create_search_from_comic_info(comic_info: ComicInfo) -> Search:
    volume = comic_info.volume if comic_info.volume else None
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=comic_info.series, volume=volume, year=year),
        issue=IssueSearch(number=comic_info.number),
    )


def _create_search_from_filename(fallback_title: str) -> Search:
    series_name = comicfn2dict(fallback_title).get("series", fallback_title).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch())


def get_search_details(
    metadata: tuple[MetronInfo | None, ComicInfo | None], fallback_title: str
) -> Search:
    metron_info, comic_info = metadata
    if metron_info and metron_info.series and metron_info.series.name:
        return _create_search_from_metron(metron_info)
    if comic_info and comic_info.series:
        return _create_search_from_comic_info(comic_info)
    return _create_search_from_filename(fallback_title)


def load_page_info(entry: Comic, comic_info: ComicInfo) -> list[Page]:
    pages = set()
    image_files = [
        x
        for x in entry.archive.get_filename_list()
        if Path(x).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    for idx, file in enumerate(image_files):
        img_file = Path(file)
        is_final_page = idx == len(image_files) - 1
        page = next((x for x in comic_info.pages if x.image == idx), None)
        pages.add(Page.from_path(file=img_file, index=idx, is_final_page=is_final_page, page=page))
    return sorted(pages)


def sync_metadata(
    search: Search, services: dict[Service, BaseService | None], settings: Settings
) -> tuple[MetronInfo | None, ComicInfo | None]:
    for service_name in settings.services.order:
        if service := services.get(service_name):
            LOGGER.info("Searching %s for matching issue", type(service).__name__)
            metron_info, comic_info = service.fetch(search=search)
            if metron_info or comic_info:
                return metron_info, comic_info
    return None, None


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
    ] = SyncOption.OUTDATED.value,
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
    setup_logging(debug=debug)
    LOGGER.info("Python v%s", python_version())
    LOGGER.info("Perdoo v%s", __version__)

    settings = Settings.load()
    settings.save()
    if debug:
        CONSOLE.print(
            {
                "target": target,
                "flags.skip-convert": skip_convert,
                "flags.sync": sync,
                "flags.skip-clean": skip_clean,
                "flags.skip-rename": skip_rename,
                "flags.clean-cache": clean_cache,
            }
        )
    if clean_cache:
        LOGGER.info("Cleaning Cache")
        recursive_delete(path=get_cache_root())
    services = get_services(settings=settings.services)
    if not services and sync != SyncOption.SKIP:
        LOGGER.warning("No external services configured")
        sync = SyncOption.SKIP

    comics = _load_comics(target=target)
    for index, entry in enumerate(comics):
        CONSOLE.rule(
            f"[{index + 1}/{len(comics)}] Importing {entry.path.name}",
            align="left",
            style="subtitle",
        )
        if not skip_convert:
            with CONSOLE.status(
                f"Converting to '{settings.output.format}'", spinner="simpleDotsScrolling"
            ):
                entry.convert(extension=settings.output.format)

        metadata: tuple[MetronInfo | None, ComicInfo | None] = (entry.metron_info, entry.comic_info)

        if sync != SyncOption.SKIP:
            search = get_search_details(metadata=metadata, fallback_title=entry.path.stem)
            last_modified = date(1900, 1, 1)
            if sync == SyncOption.OUTDATED:
                metron_info, _ = metadata
                if metron_info and metron_info.last_modified:
                    last_modified = metron_info.last_modified.date()
            if (date.today() - last_modified).days >= 28:
                metadata = sync_metadata(search=search, services=services, settings=settings)
            else:
                LOGGER.info("Metadata up-to-date")

        if not skip_clean:
            with CONSOLE.status("Cleaning Archive", spinner="simpleDotsScrolling"):
                entry.clean_archive()
        if settings.output.metron_info.create and metadata[0]:
            entry.write_metadata(metadata=metadata[0])
        if settings.output.comic_info.create and metadata[1]:
            metadata[1].pages = (
                load_page_info(entry=entry, comic_info=metadata[1])
                if settings.output.comic_info.handle_pages
                else []
            )
            entry.write_metadata(metadata=metadata[1])

        if not skip_rename:
            with CONSOLE.status("Renaming based on metadata", spinner="simpleDotsScrolling"):
                entry.rename(naming=settings.output.naming, output_folder=settings.output.folder)

    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


if __name__ == "__main__":
    app(prog_name="Perdoo")
