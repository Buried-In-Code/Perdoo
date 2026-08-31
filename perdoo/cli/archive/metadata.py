__all__ = ["register_comic_info", "register_metron_info"]

from argparse import _SubParsersAction
from pathlib import Path

from rich.panel import Panel
from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import MetadataValidationError
from shortbox.metadata import ComicInfo, Metadata, MetronInfo

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE
from perdoo.utils import display


def register_comic_info(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("comic-info", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument("target", type=existing_file, help="Comic to view details of.")
    parser.add_argument(
        "--validate", action="store_true", help="Validate the Metadata against its schema."
    )
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path="docs/img/perdoo_archive_comic-info.svg",
    )
    parser.set_defaults(func=run_comic_info)


def register_metron_info(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("metron-info", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument("target", type=existing_file, help="Comic to view details of.")
    parser.add_argument(
        "--validate", action="store_true", help="Validate the Metadata against its schema."
    )
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path="docs/img/perdoo_archive_metron-info.svg",
    )
    parser.set_defaults(func=run_metron_info)


def run(target: Path, metadata_type: type[Metadata], validate: bool = False) -> None:
    with Comic.open(target) as comic:
        if metadata := comic.get_metadata(metadata_type=metadata_type):
            if validate:
                try:
                    metadata.validate(source=comic.read_file(filename=metadata_type.filename))
                except MetadataValidationError as err:
                    CONSOLE.print(Panel.fit(str(err), border_style="logging.level.error"))
            display(data=metadata, title=f"'{comic.file.stem}' {metadata_type.__name__}")
        else:
            CONSOLE.print(f"No {metadata_type.__name__} found", style="logging.level.error")


def run_comic_info(args) -> None:  # noqa: ANN001
    run(target=args.target, metadata_type=ComicInfo, validate=args.validate)


def run_metron_info(args) -> None:  # noqa: ANN001
    run(target=args.target, metadata_type=MetronInfo, validate=args.validate)
