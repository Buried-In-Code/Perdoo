__all__ = ["app"]

from typer import Typer

from perdoo.console import CONSOLE
from perdoo.settings import Settings

app = Typer(help="Commands for managing and configuring application settings.")


@app.command(name="view", help="Display the current and default settings.")
def view() -> None:
    settings = Settings.load()
    settings.display()


@app.command(name="locate", help="Display the path to the settings file.")
def locate() -> None:
    CONSOLE.print(Settings.path)
