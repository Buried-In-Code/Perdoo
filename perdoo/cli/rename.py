__all__ = ["register"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from pathlib import Path

from natsort import humansorted, ns
from shortbox import Comic
from shortbox.errors import ArchiveCapabilityError

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import add_command, add_rename_arguments, add_target_arguments
from perdoo.console import CONSOLE
from perdoo.formats import IMAGE_EXTENSIONS, standardize_image_suffix
from perdoo.naming import build_file
from perdoo.settings import Settings
from perdoo.utils import is_same_path


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="rename",
        summary="Rename and organize comic archives using their metadata.",
        description="Rename and organize comic archives using the configured naming pattern.",
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to rename"
    )
    add_rename_arguments(parser=parser)
    parser.set_defaults(func=run)


def rename_comic(comic: Comic, image_exts: Sequence[str]) -> bool:
    renamed = False
    try:
        pad = len(str(len(comic.list_filenames())))
        idx = 0
        for filename in humansorted(comic.list_filenames(), alg=ns.NA | ns.G | ns.P):
            suffix = Path(filename).suffix.lower()
            if suffix in image_exts:
                new_name = f"{str(idx).zfill(pad)}{standardize_image_suffix(suffix)}"
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
        in_place = is_same_path(comic.file, new_file)
        if not in_place and new_file.exists() and not new_file.samefile(comic.file):
            CONSOLE.print(f"'{new_relative}' already exists, skipping")
            return Outcome.SKIPPED
        pages_renamed = rename_comic(comic=comic, image_exts=IMAGE_EXTENSIONS)
    if in_place:
        return Outcome.SUCCESS if pages_renamed else Outcome.UNCHANGED
    new_file.parent.mkdir(parents=True, exist_ok=True)
    old_relative = entry.relative_to(target) if target.is_dir() else entry.name
    CONSOLE.print(f"'{old_relative}' renamed to '{new_relative}'")
    entry.rename(new_file)
    return Outcome.SUCCESS


def delete_empty_folders(root: Path, folder: Path) -> None:
    if folder.is_dir():
        for subfolder in folder.iterdir():
            if subfolder.is_dir():
                delete_empty_folders(root=root, folder=subfolder)
        if not any(folder.iterdir()):
            folder.rmdir()
            relative = folder.relative_to(root)
            CONSOLE.print(f"Deleted empty folder: '{relative}'")


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Renaming '{args.target}'", style="title")
    settings = settings or Settings.load().save()

    def handle(entry: Path) -> Outcome:
        return rename_entry(entry=entry, target=args.target, settings=settings)

    run_on_files(files=collect_files(args), action="Renaming", handler=handle)
    if args.clean_empty:
        with CONSOLE.status("Cleaning up empty folders"):
            delete_empty_folders(root=args.target, folder=args.target)
