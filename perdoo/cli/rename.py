__all__ = ["register"]

import re
from argparse import _SubParsersAction
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal

from comic_archive import Comic
from comic_archive.errors import ArchiveCapabilityError, UnsupportedArchiveError
from comic_archive.metadata import ComicInfo, Metadata, MetronInfo
from natsort import humansorted, ns
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TaskProgressColumn, TextColumn
from rich_argparse import HelpPreviewAction

from perdoo.cli._utils import ArchiveType, RichHelpFormatter, enum_arg, existing_file_or_directory
from perdoo.console import CONSOLE
from perdoo.settings import Naming, Settings
from perdoo.utils import list_files, sanitize


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("rename", help="TODO", formatter_class=RichHelpFormatter)
    parser.add_argument(
        "target",
        type=existing_file_or_directory,
        help="Process comics from the specified file/directory.",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        action="append",
        type=enum_arg(enum_type=ArchiveType),
        choices=list(ArchiveType),
        metavar="ARCHIVE",
        help="TODO",
    )
    parser.add_argument(
        "--generate-help-preview", action=HelpPreviewAction, path="docs/img/perdoo_rename.svg"
    )
    parser.set_defaults(func=run)


def evaluate_pattern(
    metadata: Metadata,
    pattern_map: dict[str, Callable[[Metadata], str | int | None]],
    pattern: str,
    seperator: Literal["-", "_", ".", " "],
) -> str:
    def replace_match(match: re.Match) -> str:
        key = match.group("key")
        padding = match.group("padding")

        if key not in pattern_map:
            CONSOLE.print(f"Unknown pattern: {key!r}", style="logging.level.warning")
            return key
        value = pattern_map[key](metadata)

        if padding and (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
            return f"{int(value):0{padding}}"
        return sanitize(value=value, seperator=seperator) or ""

    pattern_regex = re.compile(r"{(?P<key>[a-zA-Z-]+)(?::(?P<padding>\d+))?}")
    return pattern_regex.sub(replace_match, pattern)


def from_metron_info(metadata: MetronInfo, settings: Naming) -> str:
    pattern_map = {
        "cover-date": lambda x: str(x.cover_date) if x.cover_date else None,
        "cover-day": lambda x: x.cover_date.day if x.cover_date else None,
        "cover-month": lambda x: x.cover_date.month if x.cover_date else None,
        "cover-year": lambda x: x.cover_date.year if x.cover_date else None,
        "format": lambda x: x.series.format.value if x.series.format else None,
        "id": lambda x: next(iter(i.value for i in x.ids if i.primary), None),
        "imprint": lambda x: (
            x.publisher.imprint.value if x.publisher and x.publisher.imprint else None
        ),
        "isbn": lambda x: x.gtin.isbn if x.gtin else None,
        "issue-count": lambda x: x.series.issue_count,
        "lang": lambda x: x.series.lang,
        "number": lambda x: x.number,
        "publisher-id": lambda x: x.publisher.id if x.publisher else None,
        "publisher-name": lambda x: x.publisher.name if x.publisher else None,
        "series-id": lambda x: x.series.id,
        "series-name": lambda x: x.series.name,
        "series-sort-name": lambda x: x.series.sort_name,
        "series-year": lambda x: x.series.start_year,
        "store-date": lambda x: str(x.store_date) if x.store_date else None,
        "store-year": lambda x: x.store_date.year if x.store_date else None,
        "store-month": lambda x: x.store_date.month if x.store_date else None,
        "store-day": lambda x: x.store_date.day if x.store_date else None,
        "title": lambda x: x.collection_title,
        "upc": lambda x: x.gtin.upc if x.gtin else None,
        "volume": lambda x: x.series.volume or 1,
    }
    return evaluate_pattern(
        metadata=metadata,
        pattern_map=pattern_map,
        pattern=settings.pattern,
        seperator=settings.seperator,
    )


def from_comic_info(metadata: ComicInfo, settings: Naming) -> str:
    pattern_map = {
        "cover-date": lambda x: str(x.cover_date) if x.cover_date else None,
        "cover-day": lambda x: x.day,
        "cover-month": lambda x: x.month,
        "cover-year": lambda x: x.year,
        "format": lambda x: x.format,
        "id": lambda _: None,
        "imprint": lambda x: x.imprint,
        "isbn": lambda _: None,
        "issue-count": lambda x: x.count,
        "lang": lambda x: x.language_iso,
        "number": lambda x: x.number,
        "publisher-id": lambda _: None,
        "publisher-name": lambda x: x.publisher,
        "series-id": lambda _: None,
        "series-name": lambda x: x.series,
        "series-sort-name": lambda _: None,
        "series-year": lambda x: x.volume if x.volume and x.volume > 1900 else None,
        "store-date": lambda _: None,
        "store-day": lambda _: None,
        "store-month": lambda _: None,
        "store-year": lambda _: None,
        "title": lambda x: x.title,
        "upc": lambda _: None,
        "volume": lambda x: x.volume if x.volume and x.volume < 1900 else None,
    }
    return evaluate_pattern(
        metadata=metadata,
        pattern_map=pattern_map,
        pattern=settings.pattern,
        seperator=settings.seperator,
    )


def build_file(comic: Comic, folder: Path, settings: Naming) -> Path | None:
    if metron_info := comic.get_metadata(MetronInfo):
        filename = from_metron_info(metadata=metron_info, settings=settings)
    elif comic_info := comic.get_metadata(ComicInfo):
        filename = from_comic_info(metadata=comic_info, settings=settings)
    else:
        return None
    return folder / (filename + comic.file.suffix)


def rename_comic(comic: Comic, new_filename: str, image_exts: Sequence[str]) -> None:
    try:
        pad = len(str(len(comic.list_filenames())))
        idx = 0
        for filename in humansorted(comic.list_filenames(), alg=ns.NA | ns.G | ns.P):
            suffix = Path(filename).suffix
            if suffix in image_exts:
                new_name = f"{new_filename}_{str(idx).zfill(pad)}{suffix}"
                idx += 1
                if filename != new_name:
                    CONSOLE.print(f"Renaming {filename!r} to {new_name!r}")
                    comic.rename_file(filename=filename, new_name=new_name, override=True)
    except ArchiveCapabilityError as err:
        CONSOLE.print(
            f"{err}: Consider converting to another format first", style="logging.level.warning"
        )


def run(args) -> None:  # noqa: ANN001
    settings = Settings.load().save()

    files = list_files(args.target) if args.target.is_dir() else [args.target]
    if args.ignore:
        ignore_ext = [f".{x}" for x in args.ignore]
        files = [x for x in files if x.suffix not in ignore_ext]
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        console=CONSOLE,
    )

    with progress:
        for entry in progress.track(files, description="Checking files for renaming"):
            try:
                with Comic.open(file=entry) as comic:
                    new_file = build_file(
                        comic=comic, folder=settings.output.folder, settings=settings.output.naming
                    )
                    if not new_file:
                        continue
                    rename_comic(
                        comic=comic,
                        new_filename=new_file.stem,
                        image_exts=settings.output.image_extensions,
                    )
                if new_file.exists():
                    continue
                new_file.parent.mkdir(parents=True, exist_ok=True)
                old_relative = entry.relative_to(args.target)
                new_relative = new_file.relative_to(settings.output.folder)
                CONSOLE.print(f"'{old_relative}' renamed to '{new_relative}'")
                entry.rename(new_file)
            except UnsupportedArchiveError:
                pass
