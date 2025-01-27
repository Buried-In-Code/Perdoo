import logging
from datetime import date
from enum import Enum
from pathlib import Path
from platform import python_version
from typing import Annotated

from comicfn2dict import comicfn2dict
from typer import Argument, Context, Exit, Option, Typer

from perdoo import __version__, get_cache_root, setup_logging
from perdoo.archives import CBRArchive, get_archive
from perdoo.cli import archive_app, settings_app
from perdoo.console import CONSOLE
from perdoo.main import clean_archive, convert_file, rename_file, save_metadata, sync_metadata
from perdoo.metadata import ComicInfo, MetronInfo, get_metadata
from perdoo.metadata.metron_info import InformationSource
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
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
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


def get_search_details(
    metadata: tuple[MetronInfo | None, ComicInfo | None], fallback_title: str
) -> Search:
    metron_info, comic_info = metadata

    if metron_info and metron_info.series and metron_info.series.name:
        series_id = metron_info.series.id
        source = next(iter(x.source for x in metron_info.ids if x.primary), None)
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
                comicvine=next(
                    iter(
                        x.value for x in metron_info.ids if x.source == InformationSource.COMIC_VINE
                    ),
                    None,
                ),
                marvel=next(
                    iter(x.value for x in metron_info.ids if x.source == InformationSource.MARVEL),
                    None,
                ),
                metron=next(
                    iter(x.value for x in metron_info.ids if x.source == InformationSource.METRON),
                    None,
                ),
            ),
        )
    if comic_info and comic_info.series:
        return Search(
            series=SeriesSearch(
                name=comic_info.series,
                volume=comic_info.volume
                if comic_info.volume and comic_info.volume < 1900
                else None,
                year=comic_info.volume if comic_info.volume and comic_info.volume > 1900 else None,
            ),
            issue=IssueSearch(number=comic_info.number),
        )
    series_name = comicfn2dict(fallback_title).get("series", fallback_title).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch())


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
        Settings.display(
            extras={
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

    entries = []
    for file in list_files(target) if target.is_dir() else [target]:
        try:
            entries.append(get_archive(file))
        except NotImplementedError as nie:  # noqa: PERF203
            LOGGER.error("%s, Skipping", nie)  # noqa: TRY400

    for index, entry in enumerate(entries):
        CONSOLE.rule(
            f"[{index + 1}/{len(entries)}] Importing {entry.path.name}",
            align="left",
            style="subtitle",
        )
        if not skip_convert:
            with CONSOLE.status(
                f"Converting to '{settings.output.format}'", spinner="simpleDotsScrolling"
            ):
                entry = convert_file(entry, output_format=settings.output.format)
        if entry is None or isinstance(entry, CBRArchive):
            continue

        metadata = get_metadata(archive=entry, debug=debug)

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
                clean_archive(entry=entry, settings=settings)
        save_metadata(entry=entry, metadata=metadata, settings=settings)

        if not skip_rename:
            with CONSOLE.status("Renaming based on metadata", spinner="simpleDotsScrolling"):
                rename_file(entry=entry, metadata=metadata, settings=settings, target=target.parent)

    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


if __name__ == "__main__":
    app(prog_name="Perdoo")
