__all__ = []

import logging
from pathlib import Path
from typing import Annotated

from comic_archive import Comic
from comic_archive.metadata import ComicInfo, MetronInfo
from typer import Argument, Option

from perdoo.cli._typer import app
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
    with Comic.open(target) as comic:
        LOGGER.info("Format: '%s'", type(comic._archive).__name__)  # noqa: SLF001
        if not skip_comic_info:
            if ci := comic.get_metadata(ComicInfo):
                CONSOLE.print(ci)
            else:
                CONSOLE.print("No ComicInfo found", style="logging.level.error")
        if not skip_metron_info:
            if mi := comic.get_metadata(MetronInfo):
                CONSOLE.print(mi)
            else:
                CONSOLE.print("No MetronInfo found", style="logging.level.error")
