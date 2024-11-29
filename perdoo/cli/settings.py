__all__ = ["app"]

from argparse import SUPPRESS
from typing import Annotated

from typer import Argument, Option, Typer

from perdoo.console import CONSOLE
from perdoo.settings import Settings
from perdoo.utils import flatten_dict

app = Typer(help="Commands for managing and configuring application settings.")


@app.command(name="view", help="Display the current and default settings.")
def view() -> None:
    settings = Settings.load()
    settings.display()


@app.command(name="locate", help="Display the path to the settings file.")
def locate() -> None:
    CONSOLE.print(Settings._file)  # noqa: SLF001


@app.command(name="update", help="Update the settings.")
def update(
    key: Annotated[str | None, Argument(show_default=False, help="The setting to update.")] = None,
    value: Annotated[
        str | None, Argument(show_default=False, help="The value to update the setting to.")
    ] = SUPPRESS,
    reset: Annotated[
        bool,
        Option(
            "--reset",
            help="Reset the specified setting to its default value. If no key is provided, reset all settings.",  # noqa: E501
        ),
    ] = False,
) -> None:
    if reset:
        Settings().save()
        CONSOLE.print("Settings reset")
    elif key:
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
