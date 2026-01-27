__all__ = ["CBZArchive"]

import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar

from zipremove import ZIP_DEFLATED, ZipFile, is_zipfile

from perdoo.comic.archives._base import Archive
from perdoo.comic.errors import ComicArchiveError
from perdoo.utils import list_files

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11

LOGGER = logging.getLogger(__name__)


class CBZArchive(Archive):
    EXTENSION: ClassVar[str] = ".cbz"
    IS_READABLE: ClassVar[bool] = True
    IS_WRITEABLE: ClassVar[bool] = True
    IS_EDITABLE: ClassVar[bool] = True

    @classmethod
    def is_archive(cls, path: Path) -> bool:
        if path.suffix.lower() != cls.EXTENSION:
            return False
        return is_zipfile(filename=path)

    def list_filenames(self) -> list[str]:
        try:
            with ZipFile(file=self.filepath, mode="r") as archive:
                return archive.namelist()
        except Exception as err:
            raise ComicArchiveError(f"Unable to list files from {self.filepath.name}.") from err

    def read_file(self, filename: str) -> bytes:
        try:
            with (
                ZipFile(file=self.filepath, mode="r") as archive,
                archive.open(filename) as zip_file,
            ):
                return zip_file.read()
        except Exception as err:
            raise ComicArchiveError(f"Unable to read {filename}.") from err

    def write_file(self, filename: str, data: bytes) -> None:
        try:
            with ZipFile(file=self.filepath, mode="a") as archive:
                if filename in archive.namelist():
                    removed = archive.remove(filename)
                    archive.repack([removed])
                archive.writestr(filename, data)
        except Exception as err:
            raise ComicArchiveError(f"Unable to write {filename}.") from err

    def delete_file(self, filename: str) -> None:
        if filename not in self.list_filenames():
            return
        try:
            with ZipFile(file=self.filepath, mode="a") as archive:
                removed = archive.remove(filename)
                archive.repack([removed])
        except Exception as err:
            raise ComicArchiveError(f"Unable to delete {filename}.") from err

    def rename_file(self, filename: str, new_name: str, override: bool = False) -> None:
        if filename not in self.list_filenames():
            raise ComicArchiveError(f"Unable to rename {filename} as it does not exist.")
        try:
            removed = []
            with ZipFile(file=self.filepath, mode="a") as archive:
                if new_name in archive.namelist():
                    if not override:
                        raise ComicArchiveError(
                            f"Unable to rename {filename} as {new_name} already exists."
                        )
                    removed.append(archive.remove(new_name))
                removed.append(archive.remove(archive.copy(filename, new_name)))
                archive.repack(removed)
        except ComicArchiveError:
            raise
        except Exception as err:
            raise ComicArchiveError(f"Unable to rename {filename} to {new_name}.") from err

    def extract_files(self, destination: Path) -> None:
        try:
            with ZipFile(file=self.filepath, mode="r") as archive:
                archive.extractall(path=destination)
        except Exception as err:
            raise ComicArchiveError(
                f"Unable to extract all files from {self.filepath.name} to {destination}."
            ) from err

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path:
        output_file = src.parent / (output_name + cls.EXTENSION)
        try:
            with ZipFile(file=output_file, mode="w", compression=ZIP_DEFLATED) as archive:
                for file in files:
                    archive.write(file, arcname=file.name)
            return output_file
        except Exception as err:
            raise ComicArchiveError(f"Unable to archive files to {output_file.name}.") from err

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
