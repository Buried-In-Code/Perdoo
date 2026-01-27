__all__ = []

from perdoo.cli._typer import app
from perdoo.settings import Settings


@app.command(help="Display app settings and defaults.")
def settings() -> None:
    settings = Settings.load()
    settings.display()
