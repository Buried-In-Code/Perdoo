import logging
import shutil
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from perdoo.archives import Archive, BaseArchive
from perdoo.models import ComicInfo, MetronInfo, PascalModel
from perdoo.utils import sanitize

LOGGER = logging.getLogger("perdoo")


def convert_file(entry: BaseArchive, output: Archive) -> None:
    if isinstance(entry, output.type):
        return
    LOGGER.info("Converting '%s' to '%s'", entry, output)
    output.convert(entry)


def get_metadata(archive: BaseArchive) -> tuple[MetronInfo | None, ComicInfo | None]:
    filenames = archive.list_filenames()

    def read_meta_file(cls: type[PascalModel], filename: str) -> PascalModel | None:
        if filename in filenames:
            return cls.from_bytes(content=archive.read_file(filename=filename))
        return None

    metron_info = None
    try:
        metron_info = read_meta_file(cls=MetronInfo, filename="/MetronInfo.xml") or read_meta_file(
            cls=MetronInfo, filename="MetronInfo.xml"
        )
        if metron_info:
            metron_info = cast(MetronInfo, metron_info)
    except ValidationError as ve:
        LOGGER.error("%s contains an invalid MetronInfo file: %s", archive.path.name, ve)  # noqa: TRY400
    comic_info = None
    try:
        comic_info = read_meta_file(cls=ComicInfo, filename="/ComicInfo.xml") or read_meta_file(
            cls=ComicInfo, filename="ComicInfo.xml"
        )
        if comic_info:
            comic_info = cast(ComicInfo, comic_info)
    except ValidationError as ve:
        LOGGER.error("%s contains an invalid MetronInfo file: %s", archive.path.name, ve)  # noqa: TRY400
    return metron_info, comic_info


def rename_file(entry: BaseArchive) -> None:
    metron_info, comic_info = get_metadata(archive=entry)

    new_filename = (
        metron_info.filename if metron_info else comic_info.filename if comic_info else None
    )
    if new_filename is None:
        LOGGER.warning("Not enough information to rename this comic, skipping")
        return
    if new_filename == entry.path.stem:
        return
    renamed_file = entry.path.with_stem(new_filename)
    LOGGER.info("Renaming '%s' to '%s'", entry.path.stem, renamed_file.stem)
    shutil.move(entry.path, renamed_file)
    entry.path = renamed_file


def organize_file(entry: BaseArchive, root: Path, target: Path) -> None:
    metron_info, comic_info = get_metadata(archive=entry)
    new_file_path = None
    if metron_info:
        new_file_path = root / sanitize(metron_info.publisher.name) / metron_info.series.filename
    elif comic_info:
        new_file_path = root
        if comic_info.publisher:
            new_file_path = new_file_path / sanitize(comic_info.publisher)
        if comic_info.series_filename:
            new_file_path = new_file_path / comic_info.series_filename

    if not new_file_path or new_file_path == root:
        LOGGER.warning("Not enough information to rename this comic, skipping")
        return
    if new_file_path == entry.path.parent:
        return
    new_file_path.mkdir(parents=True, exist_ok=True)
    organized_file = new_file_path / entry.path.name
    LOGGER.info(
        "Moving '%s' to '%s'", entry.path.relative_to(target), organized_file.relative_to(root)
    )
    shutil.move(entry.path, organized_file)
    entry.path = organized_file
