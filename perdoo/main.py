import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from perdoo.archives import BaseArchive, get_archive_class
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.comic_info import Page
from perdoo.services import BaseService
from perdoo.settings import Service, Settings
from perdoo.utils import Search, list_files, sanitize

LOGGER = logging.getLogger("perdoo")


def convert_file(entry: BaseArchive, output_format: str) -> BaseArchive | None:
    output = get_archive_class(output_format)
    if isinstance(entry, output):
        return entry
    LOGGER.debug("Converting '%s' to '%s'", entry.path.name, output_format)
    return output.convert(entry)


def _load_page_info(
    image_extensions: tuple[str, ...], entry: BaseArchive, comic_info: ComicInfo
) -> None:
    with TemporaryDirectory(prefix=f"{entry.path.stem}_") as temp_str:
        temp_folder = Path(temp_str)
        if not entry.extract_files(destination=temp_folder):
            return

        image_list = list_files(temp_folder, *image_extensions)
        pages = set()
        for index, img_file in enumerate(image_list):
            is_final_page = index == len(image_list) - 1
            page = next((x for x in comic_info.pages if x.image == index), None)
            pages.add(
                Page.from_path(file=img_file, index=index, is_final_page=is_final_page, page=page)
            )
        comic_info.pages = sorted(pages)


def sync_metadata(
    entry: BaseArchive,
    search: Search,
    services: dict[Service, BaseService | None],
    settings: Settings,
) -> None:
    for service_name in settings.services.order:
        if service := services.get(service_name):
            LOGGER.info("Searching %s for matching issue", type(service).__name__)
            metron_info, comic_info = service.fetch(search=search)

            if comic_info and settings.output.metadata.comic_info.create:
                if settings.output.metadata.comic_info.handle_pages:
                    LOGGER.info("Processing ComicInfo Page data")
                    _load_page_info(
                        image_extensions=settings.image_extensions,
                        entry=entry,
                        comic_info=comic_info,
                    )
                else:
                    comic_info.pages = []
                LOGGER.info("Writing ComicInfo to archive")
                entry.write_file("ComicInfo.xml", comic_info.to_bytes().decode())
            if metron_info and settings.output.metadata.metron_info.create:
                LOGGER.info("Writing MetronInfo to archive")
                entry.write_file("MetronInfo.xml", metron_info.to_bytes().decode())
            if metron_info or comic_info:
                return


def _rename_images_in_archive(
    image_extensions: tuple[str, ...], entry: BaseArchive, filename: str
) -> None:
    with TemporaryDirectory(prefix=f"{entry.path.stem}_") as temp_str:
        temp_folder = Path(temp_str)
        if not entry.extract_files(destination=temp_folder):
            return

        image_list = list_files(temp_folder, *image_extensions)
        pad_count = len(str(len(image_list)))

        for index, img_file in enumerate(image_list):
            img_filename = f"{filename}_{str(index).zfill(pad_count)}"
            if img_filename != img_file.stem:
                renamed_img = img_file.with_stem(img_filename)
                LOGGER.info("Renaming '%s' to '%s'", img_file.stem, renamed_img.stem)
                shutil.move(img_file, renamed_img)

        files = list_files(temp_folder, *image_extensions)
        files.extend([temp_folder / "ComicInfo.xml", temp_folder / "MetronInfo.xml"])
        archive_file = entry.archive_files(
            src=temp_folder, output_name=entry.path.stem, files=files
        )
        if not archive_file:
            LOGGER.critical("Unable to re-archive images")
            return

        entry.path.unlink(missing_ok=True)
        shutil.move(archive_file, entry.path)


def rename_file(
    entry: BaseArchive, metadata: tuple[MetronInfo | None, ComicInfo | None], settings: Settings
) -> None:
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
        if Path(x).suffix.casefold() in settings.image_extensions
    ):
        return

    _rename_images_in_archive(
        image_extensions=settings.image_extensions, entry=entry, filename=new_filename
    )


def _construct_new_file_path(
    metadata: tuple[MetronInfo | None, ComicInfo | None], root: Path
) -> Path | None:
    metron_info, comic_info = metadata
    output = root
    if metron_info:
        if metron_info.publisher:
            output /= sanitize(metron_info.publisher.name)
        output /= metron_info.series.filename
    elif comic_info:
        if comic_info.publisher:
            output /= sanitize(comic_info.publisher)
        if comic_info.series_filename:
            output /= comic_info.series_filename
    return output


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
    if organized_file.exists():
        LOGGER.warning("'%s' already exists, skipping", organized_file.relative_to(root))
        return
    LOGGER.info(
        "Moving '%s' to '%s'", entry.path.relative_to(target), organized_file.relative_to(root)
    )
    shutil.move(entry.path, organized_file)
    entry.path = organized_file
