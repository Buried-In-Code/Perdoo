from __future__ import annotations

__all__ = ["CBZArchive"]

import logging
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from perdoo.archives._base import BaseArchive
from perdoo.utils import list_files

LOGGER = logging.getLogger(__name__)


class CBZArchive(BaseArchive):
    def list_filenames(self: CBZArchive) -> list[str]:
        try:
            with zipfile.ZipFile(self.path, "r") as zip_file:
                return zip_file.namelist()
        except zipfile.BadZipFile:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self: CBZArchive, filename: str) -> bytes:
        try:
            with zipfile.ZipFile(self.path, "r") as zip_file:  # noqa: SIM117
                with zip_file.open(filename) as file:
                    return file.read()
        except (zipfile.BadZipFile, KeyError):
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def extract_files(self: CBZArchive, destination: Path) -> bool:
        try:
            with zipfile.ZipFile(self.path, "r") as zip_file:
                zip_file.extractall(path=destination)
            return True
        except zipfile.BadZipFile:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls: type[CBZArchive], src: Path, filename: str) -> Path | None:
        output_file = src.parent / f"{filename}.cbz"
        try:
            with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file in list_files(path=src):
                    zip_file.write(file, arcname=file.relative_to(src))
            return output_file
        except zipfile.BadZipFile:
            LOGGER.exception("")
            return None

    @staticmethod
    def convert(old_archive: BaseArchive) -> CBZArchive | None:
        with TemporaryDirectory(prefix=f"{old_archive.path.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            if not old_archive.extract_files(destination=temp_folder):
                return None
            archive_file = CBZArchive.archive_files(src=temp_folder, filename=old_archive.path.stem)
            if not archive_file:
                return None
            new_filepath = old_archive.path.parent / f"{old_archive.path.stem}.cbz"
            shutil.move(archive_file, new_filepath)
            old_archive.path.unlink(missing_ok=True)
            return CBZArchive(path=new_filepath)
