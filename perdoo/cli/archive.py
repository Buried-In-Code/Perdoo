__all__ = ["register"]

import logging
from argparse import ArgumentTypeError, _SubParsersAction
from pathlib import Path

from comic_archive import Comic
from comic_archive.errors import MetadataValidationError
from comic_archive.metadata import ComicInfo, MetronInfo
from rich.panel import Panel
from rich.pretty import Pretty
from rich_argparse import HelpPreviewAction

from perdoo.cli._help import RichHelpFormatter
from perdoo.console import CONSOLE

LOGGER = logging.getLogger(__name__)


def existing_file(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ArgumentTypeError(f"target path is not a file: {value!r}")
    if not path.exists():
        raise ArgumentTypeError(f"target file must exist: {value!r}")
    return path


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "archive", help="Inspect comic archive metadata.", formatter_class=RichHelpFormatter
    )
    parser.add_argument("target", type=existing_file, help="Comic to view details of.")
    parser.add_argument(
        "--skip-comic-info", action="store_true", help="Don't show the ComicInfo details."
    )
    parser.add_argument(
        "--skip-metron-info", action="store_true", help="Don't show the MetronInfo details."
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate the Metadata is valid for its schema."
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_archive.svg"
    )
    parser.set_defaults(func=run)


def run(args) -> None:  # noqa: ANN001
    if args.skip_comic_info and args.skip_metron_info:
        return
    with Comic.open(args.target) as comic:
        LOGGER.info("Format: '%s'", type(comic._archive).__name__)  # noqa: SLF001
        if not args.skip_comic_info:
            if ci := comic.get_metadata(metadata_type=ComicInfo):
                if args.validate:
                    try:
                        ci.validate(source=comic.read_file(filename=ComicInfo.filename))
                    except MetadataValidationError as err:
                        CONSOLE.print(err, style="logging.level.error")
                CONSOLE.print(Panel(Pretty(ci), title=f"'{comic.file.stem}' ComicInfo"))
            else:
                CONSOLE.print("No ComicInfo found", style="logging.level.error")
        if not args.skip_metron_info:
            if mi := comic.get_metadata(metadata_type=MetronInfo):
                if args.validate:
                    try:
                        mi.validate(source=comic.read_file(filename=MetronInfo.filename))
                    except MetadataValidationError as err:
                        CONSOLE.print(err, style="logging.level.error")
                CONSOLE.print(Panel(Pretty(mi), title=f"'{comic.file.stem}' MetronInfo"))
            else:
                CONSOLE.print("No MetronInfo found", style="logging.level.error")
