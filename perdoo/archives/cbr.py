__all__ = ["CBRArchive"]

import logging
from pathlib import Path
from typing import Optional

from rarfile import RarExecError, RarFile

from perdoo.archives._base import BaseArchive

LOGGER = logging.getLogger(__name__)


class CBRArchive(BaseArchive):
    def list_filenames(self) -> list[str]:
        try:
            with RarFile(self.path) as stream:
                return stream.namelist()
        except RarExecError:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self, filename: str) -> bytes:
        try:
            with RarFile(self.path) as stream:
                return stream.read(filename)
        except RarExecError:
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def remove_file(self, filename: str) -> bool:
        raise NotImplementedError("Unable to remove a file from a CBR archive.")

    def write_file(self, filename: str, data: str) -> bool:
        raise NotImplementedError("Unable to write a file to a CBR archive.")

    def extract_files(self, destination: Path) -> bool:
        try:
            with RarFile(self.path, "r") as stream:
                stream.extractall(path=destination)
            return True
        except RarExecError:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path | None:
        raise NotImplementedError("Unable to create a CBR archive.")

    @staticmethod
    def convert(old_archive: BaseArchive) -> Optional["CBRArchive"]:
        raise NotImplementedError("Unable to convert an archive to CBR.")
