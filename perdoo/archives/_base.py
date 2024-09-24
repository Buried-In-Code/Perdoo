__all__ = ["BaseArchive"]

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseArchive(ABC):
    def __init__(self, path: Path):
        self.path = path

    @abstractmethod
    def list_filenames(self) -> list[str]: ...

    @abstractmethod
    def read_file(self, filename: str) -> bytes: ...

    @abstractmethod
    def extract_files(self, destination: Path) -> bool: ...

    @classmethod
    @abstractmethod
    def archive_files(
        cls, src: Path, output_name: str, files: list[Path] | None = None
    ) -> Path | None: ...

    @staticmethod
    @abstractmethod
    def convert(old_archive: "BaseArchive") -> Optional["BaseArchive"]: ...
