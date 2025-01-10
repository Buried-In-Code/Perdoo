__all__ = [
    "BaseArchive",
    "CB7Archive",
    "CBRArchive",
    "CBTArchive",
    "CBZArchive",
    "get_archive",
    "get_archive_class",
]

from pathlib import Path
from tarfile import is_tarfile
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
    if py7zr_loaded and is_7zfile(path):
        return CB7Archive(path=path)
    raise NotImplementedError(f"{path.name} is an unsupported archive")


def get_archive_class(extension: str) -> type[BaseArchive]:
    archive_types = {"cbz": CBZArchive, "cbr": CBRArchive, "cbt": CBTArchive}
    if extension == "cb7" and py7zr_loaded:
        return CB7Archive
    if extension in archive_types:
        return archive_types[extension]
    raise NotImplementedError(f"{extension} is an unsupported archive")
