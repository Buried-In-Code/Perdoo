from __future__ import annotations

__all__ = ["BaseArchive"]

from abc import ABC, abstractmethod
from pathlib import Path


class BaseArchive(ABC):
    def __init__(self: BaseArchive, path: Path):
        self.path = path

    @abstractmethod
    def list_filenames(self: BaseArchive) -> list[str]: ...

    @abstractmethod
    def read_file(self: BaseArchive, filename: str) -> bytes: ...

    @abstractmethod
    def extract_files(self: BaseArchive, destination: Path) -> bool: ...

    @classmethod
    @abstractmethod
    def archive_files(
        cls: type[BaseArchive], src: Path, output_name: str, files: list[Path] | None = None
    ) -> Path | None: ...

    @staticmethod
    @abstractmethod
    def convert(old_archive: BaseArchive) -> BaseArchive | None: ...
