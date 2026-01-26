__all__ = ["CBTArchive"]

import logging
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar

from perdoo.comic.archive._base import Archive
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11

LOGGER = logging.getLogger(__name__)


class CBTArchive(Archive):
    EXTENSION: ClassVar[str] = ".cbt"
    IS_READABLE: ClassVar[bool] = False
    IS_WRITEABLE: ClassVar[bool] = True
    IS_EDITABLE: ClassVar[bool] = False

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

    def extract_files(self, destination: Path) -> None:
        try:
            with tarfile.open(name=self.filepath, mode="r") as archive:
                archive.extractall(path=destination, filter="data")
        except Exception as err:
            raise ComicArchiveError(f"Unable to extract files from {self.filepath.name}.") from err

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path:
        output_file = src.parent / f"{output_name}.cbt"
        try:
            with tarfile.open(name=output_file, mode="w:gz") as archive:
                for file in files:
                    archive.add(file, arcname=file.name)
            return output_file
        except Exception as err:
            raise ComicArchiveError(f"Unable to archive files to {output_file.name}") from err

    @classmethod
    def convert_from(cls, old_archive: Archive) -> Self:
        with TemporaryDirectory(prefix=f"{old_archive.filepath.stem}_") as temp_str:
            temp_folder = Path(temp_str)
            old_archive.extract_files(destination=temp_folder)
            filepath = cls.archive_files(
                src=temp_folder,
                output_name=old_archive.filepath.stem,
                files=list_files(temp_folder),
            )
            new_filepath = old_archive.filepath.with_suffix(cls.EXTENSION)
            old_archive.filepath.unlink(missing_ok=True)
            shutil.move(filepath, new_filepath)
            return cls(filepath=new_filepath)
