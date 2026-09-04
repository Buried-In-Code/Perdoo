__all__ = ["register"]

from argparse import Namespace, _SubParsersAction

from rich.panel import Panel
from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import MetadataValidationError
from shortbox.metadata import ComicInfo, Metadata, MetronInfo

from perdoo.cli._utils import RichHelpFormatter, existing_file
from perdoo.console import CONSOLE
from perdoo.utils import display

_METADATA_COMMANDS: dict[str, type[Metadata]] = {"comic-info": ComicInfo, "metron-info": MetronInfo}


def register(subparsers: _SubParsersAction) -> None:
    for command, metadata_type in _METADATA_COMMANDS.items():
        register_metadata_command(
            subparsers=subparsers, command=command, metadata_type=metadata_type
        )


def register_metadata_command(
    subparsers: _SubParsersAction, command: str, metadata_type: type[Metadata]
) -> None:
    metadata_name = metadata_type.__name__
    parser = subparsers.add_parser(
        command,
        help=f"Display {metadata_name} metadata from a comic archive.",
        description=f"Display the {metadata_name} metadata stored in a comic archive.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file,
        help=f"Comic archive whose {metadata_name} metadata to display.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=f"Validate the {metadata_name} metadata against its schema.",
    )
    parser.add_argument(
        "--generate-help-preview",
        action=HelpPreviewAction,
        path=f"docs/img/perdoo_archive_{command}.svg",
    )
    parser.set_defaults(func=run, metadata_type=metadata_type)


def run(args: Namespace) -> None:
    with Comic.open(args.target) as comic:
        if metadata := comic.get_metadata(metadata_type=args.metadata_type):
            if args.validate:
                try:
                    metadata.validate(source=comic.read_file(filename=args.metadata_type.filename))
                except MetadataValidationError as err:
                    CONSOLE.print(Panel.fit(str(err), border_style="logging.level.error"))
            display(data=metadata, title=f"'{comic.file.stem}' {args.metadata_type.__name__}")
        else:
            CONSOLE.print(f"No {args.metadata_type.__name__} found", style="logging.level.error")
