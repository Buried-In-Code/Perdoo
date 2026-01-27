__all__ = ["PY7ZR_AVAILABLE", "CB7Archive"]

import logging
import shutil
from pathlib import Path
from sys import maxsize
from tempfile import TemporaryDirectory
from typing import ClassVar

from perdoo.comic.archive._base import Archive
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    py7zr = None
    PY7ZR_AVAILABLE = False

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11


LOGGER = logging.getLogger(__name__)


class CB7Archive(Archive):
    EXTENSION: ClassVar[str] = ".cb7"
    IS_READABLE: ClassVar[bool] = True
    IS_WRITEABLE: ClassVar[bool] = True
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
                raise ComicArchiveError(f"Unable to read {filename} in {self.filepath.name}")
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

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path:
        output_file = src.parent / (output_name + cls.EXTENSION)
        try:
            with py7zr.SevenZipFile(output_file, "w") as archive:
                for file in files:
                    archive.write(file, arcname=file.name)
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
