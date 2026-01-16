__all__ = ["CBTArchive"]

import logging
import tarfile
from pathlib import Path
from typing import ClassVar

from perdoo.comic.archive._base import Archive
from perdoo.comic.errors import ComicArchiveError

LOGGER = logging.getLogger(__name__)


class CBTArchive(Archive):
    EXTENSION: ClassVar[str] = ".cbt"

    @classmethod
    def is_archive(cls, path: Path) -> bool:
        if path.suffix.lower() != cls.EXTENSION:
            return False
        return tarfile.is_tarfile(name=path)

    def list_filenames(self) -> list[str]:
        try:
            with tarfile.open(name=self.filepath, mode="r") as archive:
                return archive.getnames()
        except Exception as err:
            raise ComicArchiveError(f"Unable to list files in {self.filepath.name}") from err

    def read_file(self, filename: str) -> bytes:
        try:
            with tarfile.open(name=self.filepath, mode="r") as archive:
                return archive.extractfile(filename).read()
        except Exception as err:
            raise ComicArchiveError(f"Unable to read {filename} in {self.filepath.name}") from err

    def extract_files(self, destination: Path) -> None:
        try:
            with tarfile.open(name=self.filepath, mode="r") as archive:
                archive.extractall(path=destination, filter="data")
        except Exception as err:
            raise ComicArchiveError(f"Unable to extract files from {self.filepath.name}.") from err
