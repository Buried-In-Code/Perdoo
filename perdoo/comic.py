__all__ = [
    "SUPPORTED_IMAGE_EXTENSIONS",
    "Comic",
    "ComicArchiveError",
    "ComicMetadataError",
    "MetadataFormat",
]

import logging
import shutil
from pathlib import Path
from typing import Final, Literal, TypeVar

from darkseid.archivers import (
    PY7ZR_AVAILABLE,
    Archiver,
    ArchiverFactory,
    SevenZipArchiver,
    TarArchiver,
    ZipArchiver,
)
from darkseid.comic import (
    COMIC_RACK_FILENAME,
    METRON_INFO_FILENAME,
    SUPPORTED_IMAGE_EXTENSIONS,
    ComicArchiveError,
    ComicMetadataError,
    MetadataFormat,
)

from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.settings import Naming

LOGGER = logging.getLogger(__name__)
T = TypeVar("T", bound=ComicInfo | MetronInfo)


class Comic:
    _ZIP_EXTENSION: Final[str] = ".cbz"
    _RAR_EXTENSION: Final[str] = ".cbr"
    _TAR_EXTENSION: Final[str] = ".cbt"
    _7Z_EXTENSION: Final[str] = ".cb7"

    def __init__(self, file: Path) -> None:
        self._archiver: Archiver | None = None
        self._comic_info: ComicInfo | None = None
        self._metron_info: MetronInfo | None = None

        self._setup_archive(file=file)
        self.read_metadata(metadata_format=MetadataFormat.COMIC_INFO)
        self.read_metadata(metadata_format=MetadataFormat.METRON_INFO)

    @property
    def archive(self) -> Archiver:
        return self._archiver

    @property
    def path(self) -> Path:
        return self.archive.path

    @property
    def comic_info(self) -> ComicInfo | None:
        return self._comic_info

    @property
    def metron_info(self) -> MetronInfo | None:
        return self._metron_info

    def is_cbz(self) -> bool:
        return self.path.suffix.lower() == self._ZIP_EXTENSION

    def is_cbr(self) -> bool:
        return self.path.suffix.lower() == self._RAR_EXTENSION

    def is_cbt(self) -> bool:
        return self.path.suffix.lower() == self._TAR_EXTENSION

    def is_cb7(self) -> bool:
        return self.path.suffix.lower() == self._7Z_EXTENSION

    def _setup_archive(self, file: Path) -> None:
        if PY7ZR_AVAILABLE:
            ArchiverFactory.register_archiver(self._7Z_EXTENSION, SevenZipArchiver)
        try:
            self._archiver: Archiver = ArchiverFactory.create_archiver(path=file)
        except Exception as err:
            raise ComicArchiveError(f"Failed to create archiver for {file}: {err}") from err

    def _read_metadata_file(self, filename: str, metadata_class: type[T]) -> T | None:
        if self.archive.exists(archive_file=filename):
            return metadata_class.from_bytes(content=self.archive.read_file(archive_file=filename))
        LOGGER.info(
            "'%s' does not contain '%s', skipping %s metadata",
            self.archive.path.name,
            filename,
            metadata_class.__name__,
        )
        return None

    def read_metadata(self, metadata_format: MetadataFormat) -> None:
        if metadata_format == MetadataFormat.COMIC_INFO:
            self._comic_info = self._read_metadata_file(COMIC_RACK_FILENAME, ComicInfo)
        elif metadata_format == MetadataFormat.METRON_INFO:
            self._metron_info = self._read_metadata_file(METRON_INFO_FILENAME, MetronInfo)
        else:
            raise ComicMetadataError(f"Unsupported metadata format: {metadata_format}")

    def convert(self, extension: Literal["cbt", "cbz"]) -> None:
        check, archiver = {
            "cbt": (self.is_cbt, TarArchiver),
            "cbz": (self.is_cbz, ZipArchiver),
        }.get(extension)
        if check():
            return
        output_file = self.path.with_suffix(f".{extension}")
        with self.archive as source, archiver(path=output_file) as destination:
            LOGGER.debug("Converting '%s' to '%s'", source.path.name, destination.path.name)
            if destination.copy_from_archive(other_archive=source):
                self._archiver = destination

    def clean_archive(self) -> None:
        with self.archive as source:
            for filename in source.get_filename_list():
                filepath = Path(filename)
                if (
                    filepath.name not in {COMIC_RACK_FILENAME, METRON_INFO_FILENAME}
                    and filepath.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS
                ):
                    source.remove_files(filename_list=[filename])
                    LOGGER.info("Removed '%s' from '%s'", filename, source.path.name)

    def write_metadata(self, metadata: ComicInfo | MetronInfo | None) -> None:
        metadata_config = {
            ComicInfo: (COMIC_RACK_FILENAME, MetadataFormat.COMIC_INFO),
            MetronInfo: (METRON_INFO_FILENAME, MetadataFormat.METRON_INFO),
        }
        config = metadata_config.get(type(metadata))
        if not config:
            raise ComicMetadataError(f"Unsupported metadata type: {type(metadata)}")

        filename, format_type = config
        with self.archive as source:
            source.write_file(archive_file=filename, data=metadata.to_bytes().decode())
            self.read_metadata(metadata_format=format_type)
            LOGGER.info("Wrote %s to '%s'", type(metadata).__name__, source.path.name)

    def _get_filepath_from_metadata(self, naming: Naming) -> str | None:
        if self.metron_info:
            return self.metron_info.get_filename(settings=naming)
        if self.comic_info:
            return self.comic_info.get_filename(settings=naming)
        return None

    def _rename_images(self, base_name: str) -> None:
        with self.archive as source:
            files = [
                x
                for x in source.get_filename_list()
                if Path(x).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            ]
            pad_count = len(str(len(files))) if files else 1
            for idx, filename in enumerate(files):
                img_file = Path(filename)
                new_file = img_file.with_name(f"{base_name}_{str(idx).zfill(pad_count)}")
                if new_file.stem != img_file.stem:
                    LOGGER.info("Renaming '%s' to '%s'", img_file.stem, new_file.stem)
                    file_contents = source.read_file(archive_file=filename)
                    source.remove_files(filename_list=[filename])
                    source.write_file(archive_file=new_file.name, data=file_contents)

    def rename(self, naming: Naming, output_folder: Path) -> None:
        new_filepath = self._get_filepath_from_metadata(naming=naming)
        if new_filepath is None:
            LOGGER.warning("Not enough information to rename '%s', skipping", self.path.stem)
            return
        new_filepath = new_filepath.lstrip("/")

        output = output_folder / f"{new_filepath}.cbz"
        if output == self.path:
            return
        if output.exists():
            LOGGER.warning("'%s' already exists, skipping", output.relative_to(output_folder))
            return
        output.parent.mkdir(parents=True, exist_ok=True)

        LOGGER.info(
            "Renaming '%s' to '%s'", self.path.name, output.relative_to(output_folder.parent)
        )
        shutil.move(self.path, output)
        self.archive._path = output  # noqa: SLF001

        new_filename = self.path.stem
        if all(
            x.startswith(new_filename)
            for x in self.archive.get_filename_list()
            if Path(x).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ):
            return
        self._rename_images(base_name=new_filename)
