from __future__ import annotations

__all__ = ["CBTArchive"]

import logging
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from perdoo.archives._base import BaseArchive
from perdoo.utils import list_files

LOGGER = logging.getLogger(__name__)


class CBTArchive(BaseArchive):
    def list_filenames(self: CBTArchive) -> list[str]:
        try:
            with tarfile.open(self.path, "r") as tar:
                return tar.getnames()
        except tarfile.ReadError:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self: CBTArchive, filename: str) -> bytes:
        try:
            with tarfile.open(self.path, "r") as tar:
                return tar.extractfile(filename).read()
        except (tarfile.ReadError, KeyError):
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def extract_files(self: CBTArchive, destination: Path) -> bool:
        try:
            with tarfile.open(self.archive_file, "r") as tar:
                tar.extractall(path=destination)  # noqa: S202
            return True
        except tarfile.ReadError:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls: type[CBTArchive], src: Path, filename: str) -> Path | None:
        output_file = src.parent / f"{filename}.cbt"
        try:
            with tarfile.open(output_file, "w:gz") as tar:
                for file in list_files(path=src):
                    tar.add(file, arcname=file.relative_to(src))
            return output_file
        except tarfile.CompressionError:
            LOGGER.exception("")
            return None

    @staticmethod
    def convert(old_archive: BaseArchive) -> CBTArchive | None:
        with TemporaryDirectory(prefix=f"{old_archive.path.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            if not old_archive.extract_files(destination=temp_folder):
                return None
            archive_file = CBTArchive.archive_files(src=temp_folder, filename=old_archive.path.stem)
            if not archive_file:
                return None
            new_filepath = old_archive.path.parent / f"{old_archive.path.stem}.cbt"
            shutil.move(archive_file, new_filepath)
            old_archive.path.unlink(missing_ok=True)
            return CBTArchive(path=new_filepath)
