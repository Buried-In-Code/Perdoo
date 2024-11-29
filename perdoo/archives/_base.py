__all__ = ["BaseArchive"]

from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from perdoo.utils import list_files


class BaseArchive(ABC):
    def __init__(self, path: Path):
        self.path = path

    @abstractmethod
    def list_filenames(self) -> list[str]: ...

    @abstractmethod
    def read_file(self, filename: str) -> bytes: ...

    def remove_file(self, filename: str) -> bool:
        if filename not in self.list_filenames():
            return True
        with TemporaryDirectory() as temp_str:
            temp_folder = Path(temp_str)
            if not self.extract_files(destination=temp_folder):
                return False
            (temp_folder / filename).unlink(missing_ok=True)
            return (
                self.archive_files(
                    src=temp_folder, output_name=self.path.stem, files=list_files(temp_folder)
                )
                is not None
            )

    def write_file(self, filename: str, data: str) -> bool:
        with TemporaryDirectory() as temp_str:
            temp_folder = Path(temp_str)
            if not self.extract_files(destination=temp_folder):
                return False
            (temp_folder / filename).write_text(data)
            return (
                self.archive_files(
                    src=temp_folder, output_name=self.path.stem, files=list_files(temp_folder)
                )
                is not None
            )

    @abstractmethod
    def extract_files(self, destination: Path) -> bool: ...

    @classmethod
    @abstractmethod
    def archive_files(cls, src: Path, output_name: str, files: list[Path]) -> Path | None: ...

    @staticmethod
    @abstractmethod
    def convert(old_archive: "BaseArchive") -> Optional["BaseArchive"]: ...
