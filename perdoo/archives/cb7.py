__all__ = ["CB7Archive"]

import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from perdoo.archives._base import BaseArchive
from perdoo.utils import list_files

try:
    from py7zr import Bad7zFile, SevenZipFile

    py7zr_loaded = True
except ImportError:
    py7zr_loaded = False

LOGGER = logging.getLogger(__name__)


class CB7Archive(BaseArchive):
    def __init__(self, path: Path):
        if not py7zr_loaded:
            raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")
        super().__init__(path=path)

    def list_filenames(self) -> list[str]:
        try:
            with SevenZipFile(self.path, "r") as archive:
                return archive.getnames()
        except Bad7zFile:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self, filename: str) -> bytes:
        try:
            with SevenZipFile(self.path, "r") as archive, archive.open(filename) as file:
                return file.read()
        except (Bad7zFile, KeyError):
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def extract_files(self, destination: Path) -> bool:
        try:
            with SevenZipFile(self.path, "r") as archive:
                archive.extractall(path=destination)
            return True
        except Bad7zFile:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path | None:
        if not py7zr_loaded:
            raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")

        output_file = src.parent / f"{output_name}.cb7"
        try:
            with SevenZipFile(output_file, "w") as archive:
                for file in files:
                    archive.write(file, arcname=file.name)
            return output_file
        except Bad7zFile:
            LOGGER.exception("")
            return None

    @staticmethod
    def convert(old_archive: BaseArchive) -> Optional["CB7Archive"]:
        if not py7zr_loaded:
            raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")

        with TemporaryDirectory(prefix=f"{old_archive.path.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            if not old_archive.extract_files(destination=temp_folder):
                return None
            archive_file = CB7Archive.archive_files(
                src=temp_folder, output_name=old_archive.path.stem, files=list_files(temp_folder)
            )
            if not archive_file:
                return None
            new_file = old_archive.path.with_suffix(".cb7")
            old_archive.path.unlink(missing_ok=True)
            shutil.move(archive_file, new_file)
            return CB7Archive(path=new_file)
