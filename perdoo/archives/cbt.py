__all__ = ["CBTArchive"]

import logging
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from perdoo.archives._base import BaseArchive
from perdoo.utils import list_files

LOGGER = logging.getLogger(__name__)


class CBTArchive(BaseArchive):
    def list_filenames(self) -> list[str]:
        try:
            with tarfile.open(self.path, "r") as tar:
                return tar.getnames()
        except tarfile.ReadError:
            LOGGER.exception("Unable to read %s", self.path.name)
            return []

    def read_file(self, filename: str) -> bytes:
        try:
            with tarfile.open(self.path, "r") as tar:
                return tar.extractfile(filename).read()
        except (tarfile.ReadError, KeyError):
            LOGGER.exception("Unable to read %s", self.path.name)
            return b""

    def extract_files(self, destination: Path) -> bool:
        try:
            with tarfile.open(self.path, "r") as tar:
                for member in tar.getmembers():
                    # Check for path traversal attack
                    if (
                        member.islnk()
                        or member.issym()
                        or ".." in member.name
                        or member.name.startswith("/")
                    ):
                        LOGGER.warning(
                            "Potential path traversal attack detected in %s", self.path.name
                        )
                        return False
                    tar.extract(member, path=destination)
            return True
        except tarfile.ReadError:
            LOGGER.exception("")
            return False

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path | None:
        output_file = src.parent / f"{output_name}.cbt"
        try:
            with tarfile.open(output_file, "w:gz") as tar:
                for file in files:
                    tar.add(file, arcname=file.name)
            return output_file
        except tarfile.CompressionError:
            LOGGER.exception("")
            return None

    @staticmethod
    def convert(old_archive: BaseArchive) -> Optional["CBTArchive"]:
        with TemporaryDirectory(prefix=f"{old_archive.path.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            if not old_archive.extract_files(destination=temp_folder):
                return None
            archive_file = CBTArchive.archive_files(
                src=temp_folder, output_name=old_archive.path.stem, files=list_files(temp_folder)
            )
            if not archive_file:
                return None
            new_file = old_archive.path.with_suffix(".cbt")
            old_archive.path.unlink(missing_ok=True)
            shutil.move(archive_file, new_file)
            return CBTArchive(path=new_file)
