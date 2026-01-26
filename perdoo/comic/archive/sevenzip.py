__all__ = ["CB7Archive"]

import logging
from pathlib import Path
from sys import maxsize
from typing import ClassVar

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    py7zr = None
    PY7ZR_AVAILABLE = False

from perdoo.comic.archive._base import Archive
from perdoo.comic.errors import ComicArchiveError

LOGGER = logging.getLogger(__name__)


class CB7Archive(Archive):
    EXTENSION: ClassVar[str] = ".cb7"
    IS_READABLE: ClassVar[bool] = True
    IS_WRITEABLE: ClassVar[bool] = False
    IS_EDITABLE: ClassVar[bool] = False

    @classmethod
    def is_archive(cls, path: Path) -> bool:
        if not PY7ZR_AVAILABLE:
            return False
        if path.suffix.lower() != cls.EXTENSION:
            return False
        return py7zr.is_7zfile(file=path)

    def list_filenames(self) -> list[str]:
        try:
            with py7zr.SevenZipFile(self.filepath, "r") as archive:
                return archive.namelist()
        except Exception as err:
            raise ComicArchiveError(f"Unable to list files in {self.filepath.name}") from err

    def read_file(self, filename: str) -> bytes:
        try:
            with py7zr.SevenZipFile(self.filepath, "r") as archive:
                factory = py7zr.io.BytesIOFactory(maxsize)
                archive.extract(targets=[filename], factory=factory)
                if file_obj := factory.products.get(filename):
                    return file_obj.read()
                raise ComicArchiveError(f"Unable to read {filename} in {self.filepath.name}")  # noqa: TRY301
        except ComicArchiveError:
            raise
        except Exception as err:
            raise ComicArchiveError(f"Unable to read {filename} in {self.filepath.name}") from err

    def extract_files(self, destination: Path) -> None:
        try:
            with py7zr.SevenZipFile(file=self.filepath, mode="r") as archive:
                archive.extractall(path=destination)
        except Exception as err:
            raise ComicArchiveError(
                f"Unable to extract all files from {self.filepath.name} to {destination}"
            ) from err
