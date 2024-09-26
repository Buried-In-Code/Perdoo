import logging
import shutil
from argparse import ArgumentParser, Namespace
from datetime import date, datetime
from pathlib import Path
from platform import python_version
from tempfile import TemporaryDirectory
from typing import cast

from pydantic import ValidationError
from rich.prompt import Prompt

from perdoo import ARCHIVE_EXTENSIONS, IMAGE_EXTENSIONS, __version__, setup_logging
from perdoo.archives import BaseArchive, CB7Archive, CBTArchive, CBZArchive, get_archive
from perdoo.console import CONSOLE
from perdoo.models import ComicInfo, MetronInfo
from perdoo.models._base import InfoModel
from perdoo.models.metron_info import InformationSource
from perdoo.services import Comicvine, League, Marvel, Metron
from perdoo.settings import OutputFormat, Service, Settings
from perdoo.utils import Details, Identifications, list_files

LOGGER = logging.getLogger("perdoo")


def parse_arguments() -> Namespace:
    parser = ArgumentParser(prog="Perdoo", allow_abbrev=False)
    parser.version = __version__
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--version", action="version")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def convert_collection(path: Path, output: OutputFormat) -> None:
    format_, archive_type = {
        OutputFormat.CB7: (".cb7", CB7Archive),
        OutputFormat.CBT: (".cbt", CBTArchive),
    }.get(output, (".cbz", CBZArchive))
    formats = [ext for ext in ARCHIVE_EXTENSIONS if ext != format_]
    for file in list_files(path, *formats):
        with CONSOLE.status(
            f"Converting {file.name} to {output.name}", spinner="simpleDotsScrolling"
        ):
            archive = get_archive(path=file)
            archive_type.convert(old_archive=archive)
        LOGGER.info("[ OK ] Converting %s to %s", file.name, output.name)


def read_meta(archive: BaseArchive) -> tuple[date | None, Details | None]:
    filenames = archive.list_filenames()

    def read_meta_file(cls: type[InfoModel], filename: str) -> InfoModel | None:
        if filename in filenames:
            return cls.from_bytes(content=archive.read_file(filename=filename))
        return None

    try:
        metron_info = read_meta_file(MetronInfo, "/MetronInfo.xml") or read_meta_file(
            MetronInfo, "MetronInfo.xml"
        )
        if metron_info:
            metron_info = cast(MetronInfo, metron_info)
            series_id = metron_info.series.id if metron_info.id else None
            issue_id = metron_info.id.primary.value if metron_info.id else None
            details = Details(
                series=Identifications(
                    search=metron_info.series.name,
                    comicvine=series_id
                    if metron_info.id.primary.source == InformationSource.COMIC_VINE
                    else None,
                    league=series_id
                    if metron_info.id.primary.source == InformationSource.LEAGUE_OF_COMIC_GEEKS
                    else None,
                    marvel=series_id
                    if metron_info.id.primary.source == InformationSource.MARVEL
                    else None,
                    metron=series_id
                    if metron_info.id.primary.source == InformationSource.METRON
                    else None,
                ),
                issue=Identifications(
                    search=metron_info.number,
                    comicvine=issue_id
                    if metron_info.id.primary.source == InformationSource.COMIC_VINE
                    else None,
                    league=issue_id
                    if metron_info.id.primary.source == InformationSource.LEAGUE_OF_COMIC_GEEKS
                    else None,
                    marvel=issue_id
                    if metron_info.id.primary.source == InformationSource.MARVEL
                    else None,
                    metron=issue_id
                    if metron_info.id.primary.source == InformationSource.METRON
                    else None,
                ),
            )
            last_modified = date(1900, 1, 1)
            if metron_info.last_modified:
                last_modified = metron_info.last_modified.date()
            return last_modified, details
    except ValidationError as ve:
        LOGGER.error("%s contains an invalid MetronInfo file: %s", archive.path.name, ve)  # noqa: TRY400

    try:
        comic_info = read_meta_file(ComicInfo, "/ComicInfo.xml") or read_meta_file(
            ComicInfo, "ComicInfo.xml"
        )
        if comic_info:
            comic_info = cast(ComicInfo, comic_info)
            details = Details(
                series=Identifications(search=comic_info.series),
                issue=Identifications(search=comic_info.number),
            )
            return date(1900, 1, 1), details
    except ValidationError as ve:
        LOGGER.error("%s contains an invalid ComicInfo file: %s", archive.path.name, ve)  # noqa: TRY400

    return None, None


def load_archives(
    path: Path, output: OutputFormat, force: bool = False
) -> list[tuple[Path, BaseArchive, Details | None]]:
    archives = []
    for file in list_files(path, f".{output}"):
        archive = get_archive(path=file)
        LOGGER.debug("Reading %s", file.stem)
        last_modified, details = read_meta(archive=archive)
        if (
            not last_modified
            or not details
            or force
            or abs(date.today() - last_modified).days >= 28
        ):
            archives.append((file, archive, details))
    return archives


def fetch_from_services(
    settings: Settings, details: Details
) -> tuple[MetronInfo | None, ComicInfo | None]:
    services = {
        Service.COMICVINE: Comicvine(settings.comicvine)
        if settings.comicvine and settings.comicvine.api_key
        else None,
        Service.LEAGUE_OF_COMIC_GEEKS: League(settings.league_of_comic_geeks)
        if settings.league_of_comic_geeks
        and settings.league_of_comic_geeks.client_id
        and settings.league_of_comic_geeks.client_secret
        else None,
        Service.MARVEL: Marvel(settings.marvel)
        if settings.marvel and settings.marvel.public_key and settings.marvel.private_key
        else None,
        Service.METRON: Metron(settings.metron)
        if settings.metron and settings.metron.username and settings.metron.password
        else None,
    }

    for service_name in settings.service_order:
        service = services[service_name]
        if service:
            LOGGER.info("Fetching information from %s", type(service).__name__)
            metron_info, comic_info = service.fetch(details=details)
            if metron_info and comic_info:
                return metron_info, comic_info
    LOGGER.warning("No external services configured or data incomplete")
    return None, None


def rename_images(folder: Path, filename: str) -> None:
    image_list = list_files(folder, *IMAGE_EXTENSIONS)
    pad_count = len(str(len(image_list)))
    for index, img_file in enumerate(image_list):
        new_filename = f"{filename}_{str(index).zfill(pad_count)}{img_file.suffix}"
        if img_file.name != new_filename:
            LOGGER.info("Renamed %s to %s", img_file.name, new_filename)
            shutil.move(img_file, folder / new_filename)


def process_pages(folder: Path, comic_info: ComicInfo, filename: str) -> None:
    from perdoo.models.comic_info import Page as ComicPage

    rename_images(folder, filename)
    image_list = list_files(folder, *IMAGE_EXTENSIONS)
    comic_info_pages = set()
    for index, img_file in enumerate(image_list):
        is_final_page = index == len(image_list) - 1
        page = next((x for x in comic_info.pages if x.image == index), None)
        comic_info_pages.add(
            ComicPage.from_path(file=img_file, index=index, is_final_page=is_final_page, page=page)
        )
    comic_info.pages = sorted(comic_info_pages)


def start(settings: Settings, force: bool = False) -> None:
    LOGGER.info("Starting Perdoo")
    convert_collection(path=settings.input_folder, output=settings.output.format)

    with CONSOLE.status(
        f"Searching for {settings.output.format} files", spinner="simpleDotsScrolling"
    ):
        archives = load_archives(
            path=settings.input_folder, output=settings.output.format, force=force
        )
    LOGGER.info("[ OK ] Searching for %s files", settings.output.format)

    for file, archive, details in archives:
        LOGGER.info("Fetching information for %s", file.stem)
        details = details or Details(
            series=Identifications(search=Prompt.ask("Series title", console=CONSOLE)),
            issue=Identifications(),
        )

        metron_info, comic_info = fetch_from_services(settings=settings, details=details)
        if not metron_info:
            LOGGER.warning("Not enough information to organize and rename this comic, skipping")
            continue
        new_file = metron_info.get_file(
            root=settings.output_folder, extension=settings.output.format.value
        )

        with (
            TemporaryDirectory(prefix=f"{new_file.stem}_") as temp_str,
            CONSOLE.status(
                f"Extracting {archive.path.stem} files", spinner="simpleDotsScrolling"
            ) as status,
        ):
            temp_folder = Path(temp_str)
            if not archive.extract_files(destination=temp_folder):
                return
            LOGGER.info("[ OK ] Extracting %s files", archive.path.stem)
            status.update(f"Processing {new_file.stem} files")
            process_pages(folder=temp_folder, comic_info=comic_info, filename=new_file.stem)
            metron_info.last_modified = datetime.now()

            files = list_files(temp_folder, *IMAGE_EXTENSIONS)
            if settings.output.create_metron_info:
                metron_info_file = temp_folder / "MetronInfo.xml"
                metron_info.to_file(file=metron_info_file)
                files.append(metron_info_file)
            if comic_info and settings.output.create_comic_info:
                comic_info_file = temp_folder / "ComicInfo.xml"
                comic_info.to_file(file=comic_info_file)
                files.append(comic_info_file)

            LOGGER.info("[ OK ] Processing %s files", new_file.stem)
            status.update(f"Archiving {new_file.stem}")
            archive_file = archive.archive_files(
                src=temp_folder, output_name=archive.path.stem, files=files
            )
            if not archive_file:
                LOGGER.critical("Unable to re-archive images")
                continue
            archive.path.unlink(missing_ok=True)
            shutil.move(archive_file, archive.path)
        LOGGER.info("[ OK ] Archiving %s", new_file.stem)

        if file.relative_to(settings.input_folder) != new_file.relative_to(settings.output_folder):
            LOGGER.info(
                "Organizing comic, moving file to %s", new_file.relative_to(settings.output_folder)
            )
            new_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(file, new_file)

    with CONSOLE.status("Cleaning up empty folders", spinner="simpleDotsScrolling"):
        for folder in sorted(
            settings.input_folder.rglob("*"), key=lambda p: len(p.parts), reverse=True
        ):
            if folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
                LOGGER.info("Deleted empty folder: %s", folder)
    LOGGER.info("[ OK ] Cleaning up empty folders")


def main() -> None:
    try:
        CONSOLE.print(f"Perdoo v{__version__}")
        CONSOLE.print(f"Python v{python_version()}")

        args = parse_arguments()
        if args.debug:
            CONSOLE.print(f"Args: {args}")
        setup_logging(debug=args.debug)

        settings = Settings.load().save()
        if args.debug:
            CONSOLE.print(f"Settings: {settings}")
        start(settings=settings, force=args.force)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
