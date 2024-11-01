import logging
from argparse import SUPPRESS
from datetime import date
from enum import Enum
from pathlib import Path
from platform import python_version
from typing import Annotated

from typer import Argument, Context, Exit, Option, Typer

from perdoo import __version__, setup_logging
from perdoo.archives import CBRArchive, get_archive
from perdoo.console import CONSOLE
from perdoo.main import clean_archive, convert_file, organize_file, rename_file, sync_metadata
from perdoo.metadata import ComicInfo, MetronInfo, get_metadata
from perdoo.metadata.metron_info import InformationSource
from perdoo.services import BaseService, Comicvine, League, Marvel, Metron
from perdoo.settings import Service, Services, Settings
from perdoo.utils import (
    IssueSearch,
    Search,
    SeriesSearch,
    delete_empty_folders,
    flatten_dict,
    list_files,
)

app = Typer(help="CLI tool for managing comic collections and settings.")
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


@app.command(name="settings", help="Manage settings.")
def config(
    key: Annotated[
        str | None, Argument(show_default=False, help="The config key to retrieve or modify.")
    ] = None,
    value: Annotated[
        str | None, Argument(show_default=False, help="The value to set for the specified key.")
    ] = SUPPRESS,
    reset: Annotated[
        bool,
        Option(
            "--reset",
            help="Reset the specified config key to its default value. If no key is provided, reset all settings.",  # noqa: E501
        ),
    ] = False,
) -> None:
    if key:
        settings = Settings.load()
        if reset:
            settings_dict = flatten_dict(content=Settings().model_dump())
            if key in settings_dict:
                settings.update(key=key, value=settings_dict[key])
                settings.save()
                CONSOLE.print(f"'{key}' Reset")
            else:
                CONSOLE.print(f"No Config key: '{key}'", style="logging.level.critical")
        elif value is not SUPPRESS:
            settings.update(key=key, value=value)
            settings.save()
            CONSOLE.print(f"Updated '{key}' to {value}")
        else:
            settings_dict = flatten_dict(content=settings.model_dump())
            CONSOLE.print(settings_dict.get(key, f"No Config key: '{key}'"))
    elif reset:
        Settings().save()
        CONSOLE.print("Settings reset")
    else:
        Settings.display()


@app.command(help="View the ComicInfo/MetronInfo inside a Comic archive.")
def view(
    target: Annotated[
        Path,
        Argument(dir_okay=False, exists=True, show_default=False, help="Comic to view details of."),
    ],
    hide_comic_info: Annotated[
        bool, Option("--hide-comic-info", help="Don't show the ComicInfo details.")
    ] = False,
    hide_metron_info: Annotated[
        bool, Option("--hide-metron-info", help="Don't show the MetronInfo details.")
    ] = False,
) -> None:
    archive = get_archive(target)
    CONSOLE.print(f"Archive format: '{type(archive).__name__[:3]}'")
    metron_info, comic_info = get_metadata(archive)
    if not hide_comic_info:
        comic_info.display()
    if not hide_metron_info:
        metron_info.display()


def get_services(settings: Services) -> dict[Service, BaseService]:
    output = {}
    if settings.comicvine.api_key:
        output[Service.COMICVINE] = Comicvine(settings.comicvine)
    if settings.league_of_comic_geeks.client_id and settings.league_of_comic_geeks.client_secret:
        output[Service.LEAGUE_OF_COMIC_GEEKS] = League(settings.league_of_comic_geeks)
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
                league=series_id if source == InformationSource.LEAGUE_OF_COMIC_GEEKS else None,
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
                league=next(
                    iter(
                        x.value
                        for x in metron_info.ids
                        if x.source == InformationSource.LEAGUE_OF_COMIC_GEEKS
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
    return Search(series=SeriesSearch(name=fallback_title), issue=IssueSearch())


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
    skip_clean: Annotated[
        bool,
        Option(
            "--skip-clean",
            help="Skip removing any files not listed in the 'image_extensions' setting.",
        ),
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
    skip_rename: Annotated[
        bool,
        Option("--skip-rename", help="Skip renaming comics based on their ComicInfo/MetronInfo."),
    ] = False,
    skip_organize: Annotated[
        bool,
        Option("--skip-organize", help="Skip organize/moving comics to appropriate directories."),
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
                "flags.skip-clean": skip_clean,
                "flags.sync": sync,
                "flags.skip-rename": skip_rename,
                "flags.skip-organize": skip_organize,
            }
        )
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
        if not skip_clean:
            with CONSOLE.status("Cleaning Archive", spinner="simpleDotsScrolling"):
                clean_archive(entry=entry, settings=settings)

        if sync != SyncOption.SKIP:
            search = get_search_details(metadata=metadata, fallback_title=entry.path.stem)
            last_modified = date(1900, 1, 1)
            if sync == SyncOption.OUTDATED:
                metron_info, _ = metadata
                if metron_info and metron_info.last_modified:
                    last_modified = metron_info.last_modified.date()
            if (date.today() - last_modified).days >= 28:
                sync_metadata(entry=entry, search=search, services=services, settings=settings)
                metadata = get_metadata(archive=entry, debug=debug)
            else:
                LOGGER.info("Metadata up-to-date")

        if not skip_rename:
            with CONSOLE.status("Renaming to match metadata", spinner="simpleDotsScrolling"):
                rename_file(entry=entry, metadata=metadata, settings=settings)

        if not skip_organize:
            with CONSOLE.status("Organizing based on metadata", spinner="simpleDotsScrolling"):
                organize_file(
                    entry=entry,
                    metadata=metadata,
                    root=settings.output.folder,
                    target=target.parent,
                )

    with CONSOLE.status("Cleaning up empty folders"):
        delete_empty_folders(folder=target)


if __name__ == "__main__":
    app(prog_name="Perdoo")
