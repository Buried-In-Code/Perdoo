__all__ = ["Archive"]

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from perdoo.comic.errors import ComicArchiveError

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11


class Archive(ABC):
    _registry: ClassVar[list[type["Archive"]]] = []
    EXTENSION: ClassVar[str] = ""

    def __init__(self, filepath: Path) -> None:
        self._filepath = filepath

    def __init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__init_subclass__(**kwargs)
        Archive._registry.append(cls)

    @property
    def filepath(self) -> Path:
        return self._filepath

    @classmethod
    def load(cls, filepath: Path) -> Self:
        for _cls in cls._registry:
            if _cls.is_archive(filepath):
                return _cls(filepath=filepath)
        raise ComicArchiveError(f"Unsupported archive format: {filepath.suffix.lower()}")

    @classmethod
    @abstractmethod
    def is_archive(cls, path: Path) -> bool: ...

    @abstractmethod
    def list_filenames(self) -> list[str]: ...

    def exists(self, filename: str) -> bool:
        return filename in self.list_filenames()

    @abstractmethod
    def read_file(self, filename: str) -> bytes: ...

    def write_file(self, filename: str, data: str | bytes) -> None:  # noqa: ARG002
        raise ComicArchiveError(f"Unable to write {filename} to {self.filepath.name}.")

    def remove_file(self, filename: str) -> None:
        raise ComicArchiveError(f"Unable to delete {filename} in {self.filepath.name}.")

    @abstractmethod
    def extract_files(self, destination: Path) -> None: ...

    @classmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Self:  # noqa: ARG003
        raise ComicArchiveError(f"Unable to archive files to {output_name}.")

    @classmethod
    def convert_from(cls, old_archive: "Archive") -> Self:
        raise ComicArchiveError(
            f"Unable to convert {old_archive.filepath.name} to a {cls.EXTENSION}"
        )
