import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from perdoo.archives import BaseArchive, get_archive_class
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.comic_info import Page
from perdoo.services import BaseService
from perdoo.settings import Service, Settings
from perdoo.utils import Search, list_files

LOGGER = logging.getLogger("perdoo")


def convert_file(entry: BaseArchive, output_format: str) -> BaseArchive | None:
    output = get_archive_class(output_format)
    if isinstance(entry, output):
        return entry
    LOGGER.debug("Converting '%s' to '%s'", entry.path.name, output_format)
    return output.convert(entry)


def clean_archive(entry: BaseArchive, settings: Settings) -> None:
    for filename in entry.list_filenames():
        if Path(filename).suffix not in settings.image_extensions:
            entry.remove_file(filename=filename)
            LOGGER.info("Removed '%s' from '%s'", filename, entry.path.name)


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
    search: Search, services: dict[Service, BaseService | None], settings: Settings
) -> tuple[MetronInfo | None, ComicInfo | None]:
    for service_name in settings.services.order:
        if service := services.get(service_name):
            LOGGER.info("Searching %s for matching issue", type(service).__name__)
            metron_info, comic_info = service.fetch(search=search)
            if metron_info or comic_info:
                return metron_info, comic_info
    return None, None


def save_metadata(
    entry: BaseArchive, metadata: tuple[MetronInfo | None, ComicInfo | None], settings: Settings
) -> None:
    metron_info, comic_info = metadata
    if comic_info and settings.output.comic_info.create:
        if settings.output.comic_info.handle_pages:
            LOGGER.info("Processing ComicInfo Page data")
            _load_page_info(
                image_extensions=settings.image_extensions, entry=entry, comic_info=comic_info
            )
        else:
            comic_info.pages = []
        LOGGER.info("Writing 'ComicInfo.xml' to '%s'", entry.path.name)
        entry.write_file("ComicInfo.xml", comic_info.to_bytes().decode())
    if metron_info and settings.output.metron_info.create:
        LOGGER.info("Writing 'MetronInfo.xml' to '%s'", entry.path.name)
        entry.write_file("MetronInfo.xml", metron_info.to_bytes().decode())


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
    entry: BaseArchive,
    metadata: tuple[MetronInfo | None, ComicInfo | None],
    settings: Settings,
    target: Path,
) -> None:
    metron_info, comic_info = metadata
    new_filepath = (
        metron_info.get_filename(settings=settings.output.naming)
        if metron_info
        else comic_info.get_filename(settings=settings.output.naming)
        if comic_info
        else None
    )
    if new_filepath is None:
        LOGGER.warning("Not enough information to rename '%s', skipping", entry.path.stem)
        return
    output = settings.output.folder / f"{new_filepath}.{settings.output.format}"

    if output == entry.path:
        return
    if output.exists():
        LOGGER.warning("'%s' already exists, skipping", output.relative_to(settings.output.folder))
        return
    output.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info(
        "Renaming '%s' to '%s'",
        entry.path.relative_to(target),
        output.relative_to(settings.output.folder.parent),
    )
    shutil.move(entry.path, output)
    entry.path = output

    new_filename = output.stem

    if all(
        x.startswith(new_filename)
        for x in entry.list_filenames()
        if Path(x).suffix.casefold() in settings.image_extensions
    ):
        return

    _rename_images_in_archive(
        image_extensions=settings.image_extensions, entry=entry, filename=new_filename
    )
