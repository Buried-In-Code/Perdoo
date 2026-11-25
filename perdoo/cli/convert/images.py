__all__ = ["convert_comic_images", "register", "run"]

from argparse import Namespace, _SubParsersAction
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from natsort import humansorted
from shortbox import Comic

from perdoo.cli._runner import Outcome, collect_files, run_on_files
from perdoo.cli._utils import add_command, add_dry_run_argument, add_target_arguments
from perdoo.console import CONSOLE
from perdoo.formats import ImageFormat, standardize_image_suffix
from perdoo.images import convert_image
from perdoo.settings import Settings


def register(subparsers: _SubParsersAction) -> None:
    parser = add_command(
        subparsers=subparsers,
        name="images",
        summary="Convert the images inside comic archives to the configured image format.",
        description="Convert the images inside comic archives to the format configured in output.image-format.",  # noqa: E501
    )
    add_target_arguments(
        parser=parser, target_help="Comic archive or directory of comic archives to convert."
    )
    add_dry_run_argument(parser=parser)
    parser.set_defaults(func=run)


def convert_comic_images(
    comic: Comic, target: ImageFormat, image_extensions: Sequence[str], dry_run: bool = False
) -> Outcome:
    existing = set(comic.list_filenames())
    pages = humansorted(
        name for name in existing if PurePosixPath(name).suffix.lower() in image_extensions
    )
    changed = 0
    failed = False
    for name in pages:
        path = PurePosixPath(name)
        new_name = str(path.with_suffix(target.extension))
        if new_name == name:
            continue
        if new_name in existing:
            CONSOLE.print(
                f"Skipping {name!r} in '{comic.file.name}': {new_name!r} already exists",
                style="logging.level.warning",
            )
            failed = True
            continue
        rename_only = standardize_image_suffix(path.suffix) == target.extension
        if dry_run:
            verb = "rename" if rename_only else "convert"
            CONSOLE.print(f"Would {verb} {name!r} to {new_name!r}", style="logging.level.debug")
        elif rename_only:
            comic.rename_file(filename=name, new_name=new_name)
            CONSOLE.print(f"Renamed {name!r} to {new_name!r}")
        else:
            try:
                data = convert_image(data=comic.read_file(filename=name), target=target)
            except Exception as err:  # noqa: BLE001
                CONSOLE.print(
                    f"Unable to convert {name!r} in '{comic.file.name}': {err}",
                    style="logging.level.warning",
                )
                failed = True
                continue
            comic.write_file(filename=new_name, data=data)
            comic.remove_file(filename=name)
            CONSOLE.print(f"Converted {name!r} to {new_name!r}")
        existing.add(new_name)
        changed += 1
    if failed:
        return Outcome.FAILED
    return Outcome.SUCCESS if changed else Outcome.UNCHANGED


def run(args: Namespace, settings: Settings | None = None) -> None:
    CONSOLE.rule(f"Converting images in '{args.target}'", style="title")
    settings = settings or Settings.load().save()
    image_format = settings.output.image_format
    if image_format is None:
        formats = ", ".join(ImageFormat)
        CONSOLE.print(
            f"Skipping image conversion: set 'output.image-format' to one of {formats} to enable it",  # noqa: E501
            style="logging.level.info",
        )
        return

    def handle(entry: Path) -> Outcome:
        with Comic.open(file=entry) as comic:
            return convert_comic_images(
                comic=comic,
                target=image_format,
                image_extensions=settings.output.image_extensions,
                dry_run=args.dry_run,
            )

    run_on_files(files=collect_files(args), action="Converting", handler=handle)
