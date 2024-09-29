__all__ = ["BaseArchive", "CB7Archive", "CBTArchive", "CBZArchive", "get_archive"]

from dataclasses import dataclass
from pathlib import Path
from tarfile import is_tarfile
from typing import ClassVar
from zipfile import is_zipfile

from rarfile import is_rarfile

from perdoo.archives._base import BaseArchive
from perdoo.archives.cb7 import CB7Archive
from perdoo.archives.cbr import CBRArchive
from perdoo.archives.cbt import CBTArchive
from perdoo.archives.cbz import CBZArchive

try:
    from py7zr import is_7zfile

    py7zr_loaded = True
except ImportError:
    py7zr_loaded = False


def get_archive(path: Path) -> BaseArchive:
    if is_zipfile(path):
        return CBZArchive(path=path)
    if is_rarfile(path):
        return CBRArchive(path=path)
    if is_tarfile(path):
        return CBTArchive(path=path)
    if py7zr_loaded and is_7zfile:
        return CB7Archive(path=path)
    raise NotImplementedError(f"{path.name} is an unsupported archive")


@dataclass(frozen=True)
class Archive:
    name: str
    type: type[BaseArchive]

    @property
    def extension(self) -> str:
        return f".{self.name}"

    def __str__(self) -> str:
        return self.name


class ArchiveRegistry:
    _registry: ClassVar[dict[str, Archive]] = {
        "cb7": Archive("cb7", CB7Archive),
        "cbr": Archive("cbr", CBRArchive),
        "cbt": Archive("cbt", CBTArchive),
        "cbz": Archive("cbz", CBZArchive),
    }

    @classmethod
    def load(cls, value: str) -> Archive:
        try:
            return cls._registry[value.casefold()]
        except KeyError as ke:
            raise ValueError(f"'{value}' isn't a valid Archive") from ke
