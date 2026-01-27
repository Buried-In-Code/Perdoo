__all__ = []

import logging
from pathlib import Path
from typing import Annotated

from typer import Argument, Option

from perdoo.cli._typer import app
from perdoo.comic import Comic
from perdoo.console import CONSOLE

LOGGER = logging.getLogger(__name__)


@app.command(help="Inspect comic archive metadata.")
def archive(
    target: Annotated[
        Path,
        Argument(dir_okay=False, exists=True, show_default=False, help="Comic to view details of."),
    ],
    skip_comic_info: Annotated[
        bool, Option("--skip-comic-info", help="Don't show the ComicInfo details.")
    ] = False,
    skip_metron_info: Annotated[
        bool, Option("--skip-metron-info", help="Don't show the MetronInfo details.")
    ] = False,
) -> None:
    if skip_comic_info and skip_metron_info:
        return
    comic = Comic(filepath=target)
    LOGGER.info("Format: '%s'", type(comic.archive).__name__)
    with comic.open_session() as session:
        metron_info, comic_info = comic.read_metadata(session=session)
        if not skip_comic_info:
            if comic_info:
                comic_info.display()
            else:
                CONSOLE.print("No ComicInfo found", style="logging.level.error")
        if not skip_metron_info:
            if metron_info:
                metron_info.display()
            else:
                CONSOLE.print("No MetronInfo found", style="logging.level.error")
