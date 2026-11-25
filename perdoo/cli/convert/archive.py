__all__ = ["convert_entry", "register", "run"]

from argparse import Namespace, _SubParsersAction
from pathlib import Path

from shortbox import Comic

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import add_command, add_dry_run_argument, add_target_arguments
from perdoo.console import CONSOLE
from perdoo.formats import ArchiveFormat
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="archive",
        summary="Convert comic archives to the configured archive format.",
        description="Convert comic archives to the format configured in output.archive-format.",
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to convert."
    )
    add_dry_run_argument(parser=parser)
    parser.set_defaults(func=run)


def _standardize_suffix(entry: Path, extension: str, dry_run: bool) -> tuple[Outcome, Path]:
    if entry.suffix == extension:
        return Outcome.UNCHANGED, entry
    new_file = entry.with_suffix(extension)
    if new_file.exists() and not new_file.samefile(entry):
        CONSOLE.print(
            f"{new_file.name!r} already exists, skipping {entry.name!r}",
            style="logging.level.warning",
        )
        return Outcome.SKIPPED, entry
    if dry_run:
        CONSOLE.print(
            f"Would rename {entry.name!r} to {new_file.name!r}", style="logging.level.debug"
        )
        return Outcome.SUCCESS, entry
    entry.rename(new_file)
    return Outcome.SUCCESS, new_file


def convert_entry(
    entry: Path, archive_format: ArchiveFormat, dry_run: bool
) -> tuple[Outcome, Path]:
    extension = archive_format.extension
    with Comic.open(file=entry) as comic:
        if entry.suffix.lower() != extension:
            new_file = entry.with_suffix(extension)
            if dry_run:
                CONSOLE.print(
                    f"Would convert {entry.name!r} to {new_file.name!r}",
                    style="logging.level.debug",
                )
                return Outcome.SUCCESS, entry
            new_file = comic.convert(
                archive_type=archive_format.archive_class,
                delete_original=True,
                raise_on_existing=False,
            )
            return Outcome.SUCCESS, new_file
    return _standardize_suffix(entry=entry, extension=extension, dry_run=dry_run)


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Converting archives in '{args.target}'", style="title")
    settings = settings or Settings.load().save()
    archive_format = settings.output.archive_format
    try:
        _ = archive_format.archive_class
    except ImportError as err:
        CONSOLE.print(f"{err}; install it and retry", style="logging.level.warning")
        raise SystemExit(1) from err

    def handle(entry: Path) -> Outcome:
        outcome, new_file = convert_entry(
            entry=entry, archive_format=archive_format, dry_run=args.dry_run
        )
        if new_file != entry and entry == args.target:
            args.target = new_file
        return outcome

    run_on_files(
        files=collect_files(args), action="Converting", handler=handle, capability_hint=None
    )
