__all__ = ["CBZArchive"]

import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from perdoo.archives._base import BaseArchive
from perdoo.archives.zipfile_remove import ZipFileRemove
from perdoo.utils import list_files

LOGGER = logging.getLogger(__name__)


class CBZArchive(BaseArchive):
    def list_filenames(self) -> list[str]:
        try:
            with ZipFile(self.path, "r") as stream:
                return stream.namelist()
        except BadZipFile:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self, filename: str) -> bytes:
        try:
            with ZipFile(self.path, "r") as zip_file, zip_file.open(filename) as file:
                return file.read()
        except (BadZipFile, KeyError):
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def remove_file(self, filename: str) -> bool:
        if filename not in self.list_filenames():
            return True
        try:
            with ZipFileRemove(self.path, "a") as stream:
                stream.remove(filename)
            return True
        except BadZipFile:
            LOGGER.exception("")
            return False

    def write_file(self, filename: str, data: str) -> bool:
        try:
            with ZipFileRemove(self.path, "a") as stream:
                if filename in stream.namelist():
                    stream.remove(filename)
                stream.writestr(filename, data)
            return True
        except BadZipFile:
            LOGGER.exception("")
            return False

    def extract_files(self, destination: Path) -> bool:
        try:
            with ZipFile(self.path, "r") as stream:
                stream.extractall(path=destination)
            return True
        except BadZipFile:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path | None:
        output_file = src.parent / f"{output_name}.cbz"
        try:
            with ZipFile(output_file, "w", ZIP_DEFLATED) as stream:
                for file in files:
                    stream.write(file, arcname=file.name)
            return output_file
        except BadZipFile:
            LOGGER.exception("")
            return None

    @staticmethod
    def convert(old_archive: BaseArchive) -> Optional["CBZArchive"]:
        with TemporaryDirectory(prefix=f"{old_archive.path.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            if not old_archive.extract_files(destination=temp_folder):
                return None
            archive_file = CBZArchive.archive_files(
                src=temp_folder, output_name=old_archive.path.stem, files=list_files(temp_folder)
            )
            if not archive_file:
                return None
            new_file = old_archive.path.with_suffix(".cbz")
            old_archive.path.unlink(missing_ok=True)
            shutil.move(archive_file, new_file)
            return CBZArchive(path=new_file)
