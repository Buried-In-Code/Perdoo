import logging
from argparse import SUPPRESS
from pathlib import Path
from platform import python_version
from typing import Annotated

from typer import Argument, Context, Exit, Option, Typer

from perdoo import ARCHIVE_EXTENSIONS, __version__, setup_logging
from perdoo.console import CONSOLE
from perdoo.main import convert_files
from perdoo.settings import OutputFormat, Settings, SyncOption
from perdoo.utils import flatten_dict, list_files

app = Typer(help="CLI tool for managing comic collections and settings.")
LOGGER = logging.getLogger("perdoo")


@app.command(help="Manage configuration settings for Perdoo.")
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


@app.callback(invoke_without_command=True, help="Main command for running Perdoo.")
def main(
    ctx: Context,
    convert: Annotated[
        bool | None,
        Option(
            "--convert/--skip-convert",
            "-c/-C",
            show_default=False,
            help="Convert comics to the configured format.",
        ),
    ] = None,
    sync: Annotated[
        SyncOption | None,
        Option(
            "--sync",
            "-s",
            case_sensitive=False,
            show_default=False,
            help="Sync comic data with online services.",
        ),
    ] = None,
    rename: Annotated[
        bool | None,
        Option(
            "--rename/--skip-rename",
            "-r/-R",
            show_default=False,
            help="Rename comics based on their ComicInfo/MetronInfo.",
        ),
    ] = None,
    organize: Annotated[
        bool | None,
        Option(
            "--organize/--skip-organize",
            "-o/-O",
            show_default=False,
            help="Organize/move comics to appropriate directories.",
        ),
    ] = None,
    import_folder: Annotated[
        Path | None,
        Option(
            "--import",
            "-i",
            exists=True,
            file_okay=False,
            help="Import comics from the specified folder.",
        ),
    ] = None,
    debug: Annotated[
        bool, Option("--debug", help="Enable debug mode to show extra information.")
    ] = False,
    version: Annotated[
        bool | None, Option("--version", is_eager=True, help="Show the version and exit.")
    ] = None,
) -> None:
    if ctx.invoked_subcommand:
        return
    if version:
        CONSOLE.print(f"Perdoo v{__version__}")
        raise Exit

    setup_logging(debug=debug)
    LOGGER.info("Python v%s", python_version())
    LOGGER.info("Perdoo v%s", __version__)

    settings = Settings.load()
    if not settings._file.exists():  # noqa: SLF001
        settings.save()
    current_convert = convert if convert is not None else settings.flags.convert
    current_sync = sync if sync is not None else settings.flags.sync
    current_rename = rename if rename is not None else settings.flags.rename
    current_organize = organize if organize is not None else settings.flags.organize
    current_import_folder = (
        import_folder if import_folder is not None else settings.flags.import_folder
    )
    if debug:
        Settings.display(
            extras={
                "flags.convert": current_convert,
                "flags.sync": current_sync,
                "flags.rename": current_rename,
                "flags.organize": current_organize,
                "flags.import_folder": current_import_folder,
            }
        )

    if current_convert:
        with CONSOLE.status(
            f"Converting files to {settings.output.format}", spinner="simpleDotsScrolling"
        ):
            output_format = {OutputFormat.CB7: ".cb7", OutputFormat.CBT: ".cbt"}.get(
                settings.output.format, ".cbz"
            )
            formats = [ext for ext in ARCHIVE_EXTENSIONS if ext != output_format]
            file_conversions = list_files(settings.collection_folder, *formats)
            if current_import_folder:
                file_conversions.extend(list_files(current_import_folder, *formats))
            convert_files(files=file_conversions, output_format=settings.output.format)
        LOGGER.info("[ DONE ] Converting files to %s", settings.output.format)
    if current_sync != SyncOption.SKIP:
        if current_sync == SyncOption.OUTDATED:
            CONSOLE.print("Checking which comics need to be updated")
        CONSOLE.print("Pulling information from services")
    if current_rename:
        CONSOLE.print("Rename comic files based on their Info file contents")
    if current_organize:
        CONSOLE.print("Move comics around")


if __name__ == "__main__":
    app(prog_name="Perdoo")
