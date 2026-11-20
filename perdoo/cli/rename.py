__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from natsort import humansorted, ns
from rich_argparse import HelpPreviewAction
from shortbox import Comic
from shortbox.errors import ArchiveCapabilityError

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.naming import build_file
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "rename",
        help="Rename and organize comic archives using their metadata.",
        description="Rename and organize comic archives using the configured naming pattern.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Comic archive or directory of comic archives to rename.",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        type=enum_arg(enum_type=ArchiveType),
        choices=list(ArchiveType),
        metavar="EXT",
        help="Skip archives with this extension. Repeat to ignore multiple extensions.",
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_rename.svg"
    )
    parser.set_defaults(func=run)


def rename_comic(comic: Comic, image_exts: Sequence[str]) -> bool:
    renamed = False
    try:
        pad = len(str(len(comic.list_filenames())))
        idx = 0
        for filename in humansorted(comic.list_filenames(), alg=ns.NA | ns.G | ns.P):
            suffix = Path(filename).suffix
            if suffix in image_exts:
                new_name = f"{str(idx).zfill(pad)}{suffix}"
                idx += 1
                if filename != new_name:
                    CONSOLE.print(f"Renaming {filename!r} to {new_name!r}")
                    comic.rename_file(filename=filename, new_name=new_name, override=True)
                    renamed = True
    except ArchiveCapabilityError as err:
        CONSOLE.print(
            f"{err}: Consider converting to another format first", style="logging.level.warning"
        )
    return renamed


def rename_entry(entry: Path, target: Path, settings: Settings) -> Outcome:
    with Comic.open(file=entry) as comic:
        new_file = build_file(
            comic=comic, folder=settings.output.folder, settings=settings.output.naming
        )
        if not new_file:
            CONSOLE.print(f"'{entry.name}' has no recognised metadata, skipping")
            return Outcome.SKIPPED
        new_relative = new_file.relative_to(settings.output.folder.resolve())
        if comic.file != new_file and new_file.exists():
            CONSOLE.print(f"'{new_relative}' already exists, skipping")
            return Outcome.SKIPPED
        pages_renamed = rename_comic(comic=comic, image_exts=settings.output.image_extensions)
    if new_file.exists():
        return Outcome.SUCCESS if pages_renamed else Outcome.UNCHANGED
    new_file.parent.mkdir(parents=True, exist_ok=True)
    old_relative = entry.relative_to(target) if target.is_dir() else entry.name
    CONSOLE.print(f"'{old_relative}' renamed to '{new_relative}'")
    entry.rename(new_file)
    return Outcome.SUCCESS


def run(args: Namespace) -> None:
    settings = Settings.load().save()

    def handle(entry: Path) -> Outcome:
        return rename_entry(entry=entry, target=args.target, settings=settings)

    run_on_files(files=collect_files(args), action="Renaming", handler=handle)
