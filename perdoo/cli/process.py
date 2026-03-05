import logging
from datetime import date
from enum import Enum
from io import BytesIO
from pathlib import Path
from platform import python_version
from typing import Annotated

from comicfn2dict import comicfn2dict
from typer import Argument, Option

from perdoo import __version__, get_cache_root, setup_logging
from perdoo.cli._typer import app
from perdoo.comic import Comic
from perdoo.comic.archives import ArchiveSession
from perdoo.comic.errors import ComicArchiveError, ComicMetadataError
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.comic_info import Page, PageType
from perdoo.comic.metadata.metron_info import Id, InformationSource
from perdoo.console import CONSOLE
from perdoo.services import BaseService, Comicvine, Metron
from perdoo.settings import SETTINGS, Service
from perdoo.utils import (
    IssueSearch,
    Search,
    SeriesSearch,
    delete_empty_folders,
    list_files,
    recursive_delete,
)

LOGGER = logging.getLogger(__name__)


class SyncOption(str, Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"


def get_services() -> dict[Service, BaseService]:
    output = {}
    if SETTINGS.services.comicvine.api_key:
        output[Service.COMICVINE] = Comicvine(api_key=SETTINGS.services.comicvine.api_key)
    if SETTINGS.services.metron.username and SETTINGS.services.metron.password:
        output[Service.METRON] = Metron(
            username=SETTINGS.services.metron.username, password=SETTINGS.services.metron.password
        )
    return output


def setup_environment(
    clean_cache: bool, sync: SyncOption, debug: bool = False
) -> tuple[dict[Service, BaseService], SyncOption]:
    setup_logging(debug=debug)
    LOGGER.info("Python v%s", python_version())
    LOGGER.info("Perdoo v%s", __version__)

    if clean_cache:
        LOGGER.info("Cleaning Cache")
        recursive_delete(path=get_cache_root())

    services = get_services()
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


def prepare_comic(entry: Comic, skip_convert: bool) -> bool:
    if not skip_convert:
        entry.convert_to(SETTINGS.output.format)
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


def search_from_metron_info(metron_info: MetronInfo, filename: str) -> Search:
    series_id = metron_info.series.id
    comicvine_id = get_id(metron_info.ids, InformationSource.COMIC_VINE)
    metron_id = get_id(metron_info.ids, InformationSource.METRON)
    source = next((x.source for x in metron_info.ids if x.primary), None)
    return Search(
        series=SeriesSearch(
            name=metron_info.series.name,
            volume=metron_info.series.volume,
            year=metron_info.series.start_year,
            comicvine=int(series_id)
            if series_id and source == InformationSource.COMIC_VINE
            else None,
            metron=int(series_id) if series_id and source == InformationSource.METRON else None,
        ),
        issue=IssueSearch(
            number=metron_info.number,
            comicvine=int(comicvine_id) if comicvine_id else None,
            metron=int(metron_id) if metron_id else None,
        ),
        filename=filename,
    )


def search_from_comic_info(comic_info: ComicInfo, filename: str) -> Search:
    volume = comic_info.volume
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=comic_info.series or filename, volume=volume, year=year),
        issue=IssueSearch(number=comic_info.number),
        filename=filename,
    )


def search_from_filename(filename: str) -> Search:
    series_name = comicfn2dict(filename).get("series", filename)
    series_name = str(series_name).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch(), filename=filename)


def build_search(
    metron_info: MetronInfo | None, comic_info: ComicInfo | None, filename: str
) -> Search:
    if metron_info and metron_info.series and metron_info.series.name:
        return search_from_metron_info(metron_info=metron_info, filename=filename)
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
    entry: Comic, session: ArchiveSession, services: dict[Service, BaseService], sync: SyncOption
) -> tuple[MetronInfo | None, ComicInfo | None]:
    metron_info, comic_info = entry.read_metadata(session=session)
    if not should_sync_metadata(sync=sync, metron_info=metron_info):
        return metron_info, comic_info
    search = build_search(
        metron_info=metron_info, comic_info=comic_info, filename=entry.filepath.stem
    )
    return sync_metadata(search=search, services=services, service_order=SETTINGS.services.order)


def generate_naming(metron_info: MetronInfo | None, comic_info: ComicInfo | None) -> str | None:
    filepath = None
    if metron_info:
        filepath = metron_info.get_filename()
    if not filepath and comic_info:
        filepath = comic_info.get_filename()
    return filepath.lstrip("/") if filepath else None


def load_page_info(entry: Comic, session: ArchiveSession, comic_info: ComicInfo) -> None:
    from PIL import Image  # noqa: PLC0415

    pages = set()
    image_files = entry.list_images(image_extensions=SETTINGS.output.image_extensions)
    for idx, file in enumerate(image_files):
        page = next((x for x in comic_info.pages if x.image == idx), None)
        if page:
            page_type = page.type
        elif idx == 0:
            page_type = PageType.FRONT_COVER
        elif idx == len(image_files) - 1:
            page_type = PageType.BACK_COVER
        else:
            page_type = PageType.STORY
        if not page:
            page = Page(image=idx)
        page.type = page_type
        page_bytes = entry.read_file(session=session, filename=file.name)
        if not page_bytes:
            continue
        page.image_size = len(page_bytes)
        with Image.open(BytesIO(page_bytes)) as page_data:
            width, height = page_data.size
            page.double_page = width >= height
            page.image_height = height
            page.image_width = width
        pages.add(page)
    comic_info.pages = sorted(pages)


def apply_changes(
    entry: Comic,
    session: ArchiveSession,
    metron_info: MetronInfo | None,
    comic_info: ComicInfo | None,
    skip_clean: bool,
    skip_rename: bool,
) -> str | None:
    local_metron_info, local_comic_info = entry.read_metadata(session=session)
    if local_metron_info != metron_info:
        if metron_info:
            session.write(filename=MetronInfo.FILENAME, data=metron_info.to_bytes())
        else:
            session.delete(filename=MetronInfo.FILENAME)

    if comic_info and SETTINGS.output.comic_info.handle_pages:
        load_page_info(entry=entry, session=session, comic_info=comic_info)
    if local_comic_info != comic_info:
        if comic_info:
            session.write(filename=ComicInfo.FILENAME, data=comic_info.to_bytes())
        else:
            session.delete(filename=ComicInfo.FILENAME)

    if not skip_clean:
        for extra in entry.list_extras(image_extensions=SETTINGS.output.image_extensions):
            session.delete(filename=extra.name)

    naming = None
    if not skip_rename and (
        naming := generate_naming(metron_info=metron_info, comic_info=comic_info)
    ):
        images = entry.list_images(image_extensions=SETTINGS.output.image_extensions)
        stem = Path(naming).stem
        pad = len(str(len(images)))
        for idx, img in enumerate(images):
            new_name = f"{stem}_{str(idx).zfill(pad)}{img.suffix}"
            if img.name != new_name:
                session.rename(filename=img.name, new_name=new_name)
    return naming


@app.command(help="Process comics by converting, syncing metadata, and organizing them.")
def process(
    target: Annotated[
        Path,
        Argument(
            exists=True, help="Process comics from the specified file/folder.", show_default=False
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
        bool, Option("--skip-clean", help="Skip removing any non-image/MetronInfo/ComicInfo files.")
    ] = False,
    skip_rename: Annotated[
        bool,
        Option(
            "--skip-rename",
            help="Skip organizing and renaming comics based on their MetronInfo/ComicInfo.",
        ),
    ] = False,
    clean_cache: Annotated[
        bool, Option("--clean", "-c", show_default=False, help="Remove all cached files.")
    ] = False,
    debug: Annotated[
        bool, Option("--debug", help="Enable debug mode to show extra information.")
    ] = False,
) -> None:
    services, sync = setup_environment(clean_cache=clean_cache, sync=sync, debug=debug)

    comics = load_comics(target=target)
    total = len(comics)
    for index, entry in enumerate(comics, start=1):
        CONSOLE.rule(
            f"[{index}/{total}] Importing {entry.filepath.name}", align="left", style="subtitle"
        )

        if not prepare_comic(entry=entry, skip_convert=skip_convert):
            continue
        with entry.open_session() as session:
            metron_info, comic_info = resolve_metadata(
                entry=entry, session=session, services=services, sync=sync
            )
            naming = apply_changes(
                entry=entry,
                session=session,
                metron_info=metron_info,
                comic_info=comic_info,
                skip_clean=skip_clean,
                skip_rename=skip_rename,
            )
        if naming:
            entry.move_to(naming=naming, output_folder=SETTINGS.output.folder)
    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


@app.command(
    name="import",
    deprecated=True,
    help="Use `perdoo process` instead.\nImport comics into your collection using Perdoo.",
)
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
    LOGGER.warning("`perdoo import` is deprecated; use `perdoo process` instead.")
    return process(
        target=target,
        skip_convert=skip_convert,
        sync=sync,
        skip_clean=skip_clean,
        skip_rename=skip_rename,
        clean_cache=clean_cache,
        debug=debug,
    )
