__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from pathspec import GitIgnoreSpec
from shortbox import Comic

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import add_command, add_dry_run_argument, add_target_arguments
from perdoo.console import CONSOLE
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="clean",
        summary="Remove configured unwanted files and folders from comic archives.",
        description="Remove files and folders matching the .gitignore-style patterns configured in output.clean-targets from comic archives.",  # noqa: E501
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to clean."
    )
    add_dry_run_argument(parser=parser)
    parser.set_defaults(func=run)


def clean_comic(comic: Comic, removals: Sequence[str], dry_run: bool = False) -> Outcome:
    spec = GitIgnoreSpec.from_lines(removals)
    removed = [name for name in comic.list_filenames() if spec.match_file(name)]
    for filename in removed:
        if dry_run:
            CONSOLE.print(f"Would remove {filename!r}", style="logging.level.debug")
            continue
        CONSOLE.print(f"Removing {filename!r}")
        comic.remove_file(filename=filename)
    return Outcome.SUCCESS if removed else Outcome.UNCHANGED


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Cleaning '{args.target}'", style="title")
    settings = settings or Settings.load().save()

    def handle(entry: Path) -> Outcome:
        with Comic.open(file=entry) as comic:
            return clean_comic(comic=comic, removals=settings.removals, dry_run=args.dry_run)

    run_on_files(files=collect_files(args), action="Cleaning", handler=handle)
