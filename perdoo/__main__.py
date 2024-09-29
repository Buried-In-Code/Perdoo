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
from perdoo.main import convert_file, organize_file, rename_file, sync_metadata
from perdoo.models import ComicInfo, MetronInfo, get_metadata
from perdoo.models.metron_info import InformationSource
from perdoo.services import BaseService, Comicvine, League, Marvel, Metron
from perdoo.settings import Service, Settings
from perdoo.utils import Details, Identifications, flatten_dict, list_files

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
        raise ValueError(f"`{value}` isn't a valid SyncOption")

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


@app.command(help="Manage settings.")
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


def get_services(settings: Settings) -> dict[Service, BaseService]:
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


def get_details(
    metadata: tuple[MetronInfo | None, ComicInfo | None], fallback_title: str
) -> Details:
    metron_info, comic_info = metadata

    if metron_info:
        series_id = metron_info.series.id if metron_info.id else None
        issue_id = metron_info.id.primary.value if metron_info.id else None
        return Details(
            series=Identifications(
                search=metron_info.series.name,
                comicvine=series_id
                if metron_info.id.primary.source == InformationSource.COMIC_VINE
                else None,
                league=series_id
                if metron_info.id.primary.source == InformationSource.LEAGUE_OF_COMIC_GEEKS
                else None,
                marvel=series_id
                if metron_info.id.primary.source == InformationSource.MARVEL
                else None,
                metron=series_id
                if metron_info.id.primary.source == InformationSource.METRON
                else None,
            ),
            issue=Identifications(
                search=metron_info.number,
                comicvine=issue_id
                if metron_info.id.primary.source == InformationSource.COMIC_VINE
                else None,
                league=issue_id
                if metron_info.id.primary.source == InformationSource.LEAGUE_OF_COMIC_GEEKS
                else None,
                marvel=issue_id
                if metron_info.id.primary.source == InformationSource.MARVEL
                else None,
                metron=issue_id
                if metron_info.id.primary.source == InformationSource.METRON
                else None,
            ),
        )
    if comic_info:
        return Details(
            series=Identifications(search=comic_info.series),
            issue=Identifications(search=comic_info.number),
        )
    return Details(series=Identifications(search=fallback_title), issue=Identifications())


@app.command(help="Run Perdoo.")
def run(
    target: Annotated[
        Path,
        Argument(
            exists=True, help="Import comics from the specified file/folder.", show_default=False
        ),
    ],
    skip_convert: Annotated[
        bool, Option("--skip-convert", help="Convert comics to the configured format.")
    ] = False,
    sync: Annotated[
        SyncOption,
        Option("--sync", "-s", case_sensitive=False, help="Sync comic data with online services."),
    ] = SyncOption.OUTDATED.value,
    skip_rename: Annotated[
        bool, Option("--skip-rename", help="Rename comics based on their ComicInfo/MetronInfo.")
    ] = False,
    skip_organize: Annotated[
        bool, Option("--skip-organize", help="Organize/move comics to appropriate directories.")
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
                "flags.skip-rename": skip_rename,
                "flags.skip-organize": skip_organize,
            }
        )
    services = get_services(settings=settings)
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
        CONSOLE.rule(f"[{index + 1}/{len(entries)}] Importing {entry.path.name}")
        if not skip_convert:
            with CONSOLE.status(
                f"Converting to {settings.output.archive_format}", spinner="simpleDotsScrolling"
            ):
                entry = convert_file(entry, output=settings.output.archive_format)
        if entry is None or isinstance(entry, CBRArchive):
            continue

        if sync != SyncOption.SKIP:
            metadata = get_metadata(archive=entry, debug=debug)
            details = get_details(metadata=metadata, fallback_title=entry.path.stem)
            last_modified = date(1900, 1, 1)
            if sync == SyncOption.OUTDATED:
                metron_info, _ = metadata
                if metron_info and metron_info.last_modified:
                    last_modified = metron_info.last_modified.date()
            if (date.today() - last_modified).days >= 28:
                sync_metadata(
                    entry=entry,
                    details=details,
                    services=services,
                    service_order=settings.service_order,
                    create_metron_info=settings.output.create_metron_info,
                    create_comic_info=settings.output.create_comic_info,
                )
        metadata = get_metadata(archive=entry, debug=debug)

        if not skip_rename:
            with CONSOLE.status("Renaming to match metadata", spinner="simpleDotsScrolling"):
                rename_file(entry=entry, metadata=metadata)

        if not skip_organize:
            with CONSOLE.status("Organizing based on metadata", spinner="simpleDotsScrolling"):
                organize_file(
                    entry=entry,
                    metadata=metadata,
                    root=settings.collection_folder,
                    target=target.parent,
                )


if __name__ == "__main__":
    app(prog_name="Perdoo")
