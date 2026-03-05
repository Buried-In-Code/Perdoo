__all__ = []

from perdoo.cli._typer import app
from perdoo.settings import SETTINGS


@app.command(help="Display app settings and defaults.")
def settings() -> None:
    SETTINGS.display()
