__all__ = ["app"]

from pathlib import Path
from typing import Annotated

from typer import Argument, Option, Typer

from perdoo.comic import Comic
from perdoo.console import CONSOLE

app = Typer(help="Commands for inspecting and managing comic archive metadata.")


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
    comic = Comic(file=target)
    CONSOLE.print(f"Archive format: '{comic.path.suffix}'")
    if not hide_metron_info:
        comic.metron_info.display()
    if not hide_comic_info:
        comic.comic_info.display()
