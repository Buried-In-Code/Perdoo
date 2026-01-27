__all__ = ["ArchiveSession"]

import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType

from perdoo.comic.archives import Archive
from perdoo.comic.errors import ComicArchiveError
from perdoo.console import CONSOLE
from perdoo.utils import list_files

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11

LOGGER = logging.getLogger(__name__)


class ArchiveSession:
    def __init__(self, archive: Archive) -> None:
        self._archive = archive
        self._temp_dir: TemporaryDirectory | None = None
        self._folder: Path | None = None
        self._extracted = False
        self._updated = False

    def __enter__(self) -> Self:
        if self._archive.IS_EDITABLE:
            return self

        self._temp_dir = TemporaryDirectory()
        self._folder = Path(self._temp_dir.name)
        with CONSOLE.status(
            f"Extracting '{self._archive.filepath}' to '{self._folder}'",
            spinner="simpleDotsScrolling",
        ):
            self._archive.extract_files(destination=self._folder)
        self._extracted = True
        self._updated = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None and self._extracted and self._updated:
                with CONSOLE.status(
                    f"Archiving '{self._folder}' to '{self._archive.filepath}'",
                    spinner="simpleDotsScrolling",
                ):
                    filepath = self._archive.archive_files(
                        src=self._folder,
                        output_name=self._archive.filepath.stem,
                        files=list_files(path=self._folder),
                    )
                    self._archive.filepath.unlink(missing_ok=True)
                    shutil.move(filepath, self._archive.filepath)
        finally:
            if self._temp_dir:
                self._temp_dir.cleanup()
            self._folder = None
            self._extracted = False

    def list(self) -> list[str]:
        if self._archive.IS_EDITABLE:
            return self._archive.list_filenames()
        return [p.name for p in self._folder.iterdir()]

    def contains(self, filename: str) -> bool:
        return filename in self.list()

    def read(self, filename: str) -> bytes:
        if self._archive.IS_READABLE:
            return self._archive.read_file(filename=filename)
        return (self._folder / filename).read_bytes()

    def write(self, filename: str, data: str | bytes) -> None:
        LOGGER.info("Writing '%s'", filename)
        if isinstance(data, str):
            data = data.encode("UTF-8")
        if self._archive.IS_EDITABLE:
            self._archive.write_file(filename=filename, data=data)
        else:
            (self._folder / filename).write_bytes(data)
        self._updated = True

    def delete(self, filename: str) -> None:
        LOGGER.info("Deleting '%s'", filename)
        if self._archive.IS_EDITABLE:
            self._archive.delete_file(filename=filename)
        else:
            (self._folder / filename).unlink(missing_ok=True)
        self._updated = True

    def rename(self, filename: str, new_name: str, override: bool = False) -> None:
        LOGGER.info("Renaming '%s' to '%s'", filename, new_name)
        if self._archive.IS_EDITABLE:
            self._archive.rename_file(filename=filename, new_name=new_name, override=override)
        else:
            src = self._folder / filename
            if not src.exists():
                raise ComicArchiveError(f"Unable to rename '{src}' as it does not exist.")
            dest = self._folder / new_name
            if dest.exists() and not override:
                raise ComicArchiveError(f"Unable to rename '{src}' as '{dest}' already exists.")
            shutil.move(src, dest)
        self._updated = True
