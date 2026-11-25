__all__ = [
    "IMAGE_EXTENSIONS",
    "ArchiveFormat",
    "ArchiveType",
    "ImageFormat",
    "standardize_image_suffix",
]

from enum import StrEnum
from typing import Self

from shortbox import archives
from shortbox.archives import Archive

_IMAGE_SUFFIX_ALIASES = {".jpeg": ".jpg"}


def standardize_image_suffix(suffix: str) -> str:
    suffix = suffix.lower()
    return _IMAGE_SUFFIX_ALIASES.get(suffix, suffix)


class _Extension(StrEnum):
    @classmethod
    def _missing_(cls, value: object) -> Self | None:
        return next((member for member in cls if member.value == str(value).lower()), None)

    @property
    def extension(self) -> str:
        return f".{self.value}"


class ArchiveType(_Extension):
    CB7 = "cb7"
    CBR = "cbr"
    CBT = "cbt"
    CBZ = "cbz"
    PDF = "pdf"


class ArchiveFormat(_Extension):
    CBZ = "cbz"
    CBT = "cbt"
    CB7 = "cb7"

    @property
    def archive_class(self) -> type[Archive]:
        name = {"cbz": "ZipArchive", "cbt": "TarArchive", "cb7": "SevenZipArchive"}[self.value]
        if (archive_class := getattr(archives, name, None)) is None:
            raise ImportError(f"{self.value!r} output requires `perdoo[{self.value}]`")
        return archive_class


class ImageFormat(_Extension):
    JPG = "jpg"
    PNG = "png"
    WEBP = "webp"
    JXL = "jxl"

    @property
    def pillow_format(self) -> str:
        return "JPEG" if self is ImageFormat.JPG else self.name


IMAGE_EXTENSIONS = (*(x.extension for x in ImageFormat), ".jpeg")
