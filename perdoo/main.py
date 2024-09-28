import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from perdoo import IMAGE_EXTENSIONS
from perdoo.archives import Archive, BaseArchive
from perdoo.models import ComicInfo, MetronInfo
from perdoo.services import BaseService
from perdoo.settings import Service
from perdoo.utils import Details, list_files, sanitize

LOGGER = logging.getLogger("perdoo")


def convert_file(entry: BaseArchive, output: Archive) -> BaseArchive | None:
    if isinstance(entry, output.type):
        return entry
    LOGGER.info("Converting '%s' to '%s'", entry, output)
    return output.convert(entry)


def sync_metadata(
    entry: BaseArchive,
    details: Details,
    services: dict[Service, BaseService | None],
    service_order: list[Service],
    create_metron_info: bool,
    create_comic_info: bool,
) -> None:
    for service_name in service_order:
        if service := services.get(service_name):
            LOGGER.info("Searching %s for matches", type(service).__name__)
            metron_info, comic_info = service.fetch(details=details)

            if metron_info and create_metron_info:
                entry.write_file("MetronInfo.xml", metron_info.to_bytes().decode())
            if comic_info and create_comic_info:
                entry.write_file("ComicInfo.xml", comic_info.to_bytes().decode())
            if metron_info or comic_info:
                return


def _rename_images_in_archive(entry: BaseArchive, filename: str) -> None:
    with TemporaryDirectory(prefix=f"{entry.path.stem}_") as temp_str:
        temp_folder = Path(temp_str)
        if not entry.extract_files(destination=temp_folder):
            return

        image_list = list_files(temp_folder, *IMAGE_EXTENSIONS)
        pad_count = len(str(len(image_list)))

        for index, img_file in enumerate(image_list):
            img_filename = f"{filename}_{str(index).zfill(pad_count)}"
            if img_filename != img_file.stem:
                renamed_img = img_file.with_stem(img_filename)
                LOGGER.info("Renaming '%s' to '%s'", img_file.stem, renamed_img.stem)
                shutil.move(img_file, renamed_img)

        archive_file = entry.archive_files(src=temp_folder, output_name=entry.path.stem)
        if not archive_file:
            LOGGER.critical("Unable to re-archive images")
            return

        entry.path.unlink(missing_ok=True)
        shutil.move(archive_file, entry.path)


def rename_file(entry: BaseArchive, metadata: tuple[MetronInfo | None, ComicInfo | None]) -> None:
    metron_info, comic_info = metadata
    new_filename = (
        metron_info.filename if metron_info else comic_info.filename if comic_info else None
    )

    if new_filename is None:
        LOGGER.warning("Not enough information to rename '%s', skipping", entry.path.stem)
        return

    if new_filename != entry.path.stem:
        renamed_file = entry.path.with_stem(new_filename)
        LOGGER.info("Renaming '%s' to '%s'", entry.path.stem, renamed_file.stem)
        shutil.move(entry.path, renamed_file)
        entry.path = renamed_file

    if all(
        x.startswith(new_filename)
        for x in entry.list_filenames()
        if Path(x).suffix.casefold() in IMAGE_EXTENSIONS
    ):
        return

    _rename_images_in_archive(entry=entry, filename=new_filename)


def _construct_new_file_path(
    metadata: tuple[MetronInfo | None, ComicInfo | None], root: Path
) -> Path | None:
    metron_info, comic_info = metadata
    if metron_info:
        return root / sanitize(metron_info.publisher.name) / metron_info.series.filename
    if comic_info:
        output = root
        if comic_info.publisher:
            output /= sanitize(comic_info.publisher)
        if comic_info.series_filename:
            output /= comic_info.series_filename
        return output
    return None


def organize_file(
    entry: BaseArchive,
    metadata: tuple[MetronInfo | None, ComicInfo | None],
    root: Path,
    target: Path,
) -> None:
    new_file_path = _construct_new_file_path(metadata=metadata, root=root)

    if not new_file_path or new_file_path == root:
        LOGGER.warning("Not enough information to organize '%s', skipping", entry.path.stem)
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
