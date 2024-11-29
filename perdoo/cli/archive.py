__all__ = ["app"]

from pathlib import Path
from typing import Annotated

from typer import Argument, Option, Typer

from perdoo.archives import get_archive
from perdoo.console import CONSOLE
from perdoo.metadata import get_metadata

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
    archive = get_archive(path=target)
    CONSOLE.print(f"Archive format: '{type(archive).__name__[:3]}'")
    metron_info, comic_info = get_metadata(archive=archive)
    if not hide_comic_info:
        comic_info.display()
    if not hide_metron_info:
        metron_info.display()
