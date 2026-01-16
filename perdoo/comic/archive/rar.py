__all__ = ["CBRArchive"]

import logging
from pathlib import Path
from typing import ClassVar

from rarfile import RarFile, is_rarfile

from perdoo.comic.archive._base import Archive
from perdoo.comic.errors import ComicArchiveError

LOGGER = logging.getLogger(__name__)


class CBRArchive(Archive):
    EXTENSION: ClassVar[str] = ".cbr"

    @classmethod
    def is_archive(cls, path: Path) -> bool:
        if path.suffix.lower() != cls.EXTENSION:
            return False
        return is_rarfile(xfile=path)

    def list_filenames(self) -> list[str]:
        try:
            with RarFile(file=self.filepath, mode="r") as archive:
                return archive.namelist()
        except Exception as err:
            raise ComicArchiveError(f"Unable to list files in {self.filepath.name}") from err

    def read_file(self, filename: str) -> bytes:
        try:
            with RarFile(file=self.filepath, mode="r") as archive:
                return archive.read(filename)
        except Exception as err:
            raise ComicArchiveError(f"Unable to read {filename} in {self.filepath.name}.") from err

    def extract_files(self, destination: Path) -> None:
        try:
            with RarFile(file=self.filepath, mode="r") as archive:
                archive.extractall(path=destination)
        except Exception as err:
            raise ComicArchiveError(f"Unable to extract files from {self.filepath.name}.") from err
