import logging
from argparse import SUPPRESS
from enum import Enum
from pathlib import Path
from platform import python_version
from typing import Annotated

from typer import Argument, Context, Exit, Option, Typer

from perdoo import __version__, setup_logging
from perdoo.archives import CBRArchive, get_archive
from perdoo.console import CONSOLE, create_progress
from perdoo.main import convert_file, organize_file, rename_file
from perdoo.settings import Settings
from perdoo.utils import flatten_dict, list_files

app = Typer(help="CLI tool for managing comic collections and settings.")
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
        raise ValueError(f"`{value}` isn't a valid SyncOption")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

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
            if key in settings_dict:
                CONSOLE.print(settings_dict[key])
            else:
                CONSOLE.print(f"No Config key: '{key}'", style="logging.level.critical")
    elif reset:
        Settings().save()
        CONSOLE.print("Settings reset")
    else:
        Settings.display()


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

    import_files = list_files(target) if target.is_dir() else [target]
    entries = []
    for file in import_files:
        try:
            entries.append(get_archive(file))
        except NotImplementedError as nie:  # noqa: PERF203
            LOGGER.error("%s, Skipping", nie)  # noqa: TRY400
    if not skip_convert:
        with create_progress() as progress:
            for entry in progress.track(
                entries, description=f"Converting to {settings.output.archive_format}"
            ):
                convert_file(entry=entry, output=settings.output.archive_format)
    else:
        entries = [x for x in entries if not isinstance(x, CBRArchive)]
    if sync != SyncOption.SKIP:
        if sync == SyncOption.OUTDATED:
            CONSOLE.print("Checking which comics need to be updated")
        CONSOLE.print("Pulling information from services")
    if not skip_rename:
        with create_progress() as progress:
            for entry in progress.track(entries, description="Renaming files to match metadata"):
                rename_file(entry=entry)
    if not skip_organize:
        with create_progress() as progress:
            for entry in progress.track(entries, description="Organizing files based on metadata"):
                organize_file(
                    entry=entry,
                    root=settings.collection_folder,
                    target=target.parent,
                )


if __name__ == "__main__":
    app(prog_name="Perdoo")
