__all__ = ["IMAGE_EXTENSIONS", "Comic"]

import logging
import shutil
from pathlib import Path
from typing import Final, Literal

from natsort import humansorted, ns

from perdoo.comic.archives import Archive, ArchiveSession, CB7Archive, CBTArchive, CBZArchive
from perdoo.comic.metadata import ComicInfo, MetronInfo

LOGGER = logging.getLogger(__name__)

METADATA_FILENAMES: Final[frozenset[str]] = frozenset([MetronInfo.FILENAME, ComicInfo.FILENAME])
IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset([".png", ".jpg", ".jpeg", ".webp", ".jxl"])


class Comic:
    def __init__(self, filepath: Path):
        self._archive: Archive = Archive.load(filepath=filepath)

    @property
    def archive(self) -> Archive:
        return self._archive

    @property
    def filepath(self) -> Path:
        return self.archive.filepath

    def open_session(self) -> ArchiveSession:
        return ArchiveSession(self.archive)

    def convert_to(self, extension: Literal["cbz", "cbt", "cb7"]) -> None:
        cls = {"cbz": CBZArchive, "cbt": CBTArchive, "cb7": CB7Archive}[extension]
        if not isinstance(self.archive, cls):
            self._archive = cls.convert_from(old_archive=self.archive)

    def read_metadata(self, session: ArchiveSession) -> tuple[MetronInfo | None, ComicInfo | None]:
        metron_info = None
        if session.contains(filename=MetronInfo.FILENAME):
            metron_info = MetronInfo.from_bytes(content=session.read(filename=MetronInfo.FILENAME))
        comic_info = None
        if session.contains(filename=ComicInfo.FILENAME):
            comic_info = ComicInfo.from_bytes(content=session.read(filename=ComicInfo.FILENAME))
        return metron_info, comic_info

    def list_images(self) -> list[Path]:
        return humansorted(
            [
                Path(name)
                for name in self.archive.list_filenames()
                if Path(name).suffix.lower() in IMAGE_EXTENSIONS
            ],
            alg=ns.NA | ns.G | ns.P,
        )

    def list_extras(self) -> list[Path]:
        return humansorted(
            [
                Path(name)
                for name in self.archive.list_filenames()
                if name not in METADATA_FILENAMES
                and Path(name).suffix.lower() not in IMAGE_EXTENSIONS
            ],
            alg=ns.NA | ns.G | ns.P,
        )

    def validate_naming(self, naming: str) -> bool:
        template = Path(naming).stem
        return all(img.name.startswith(template) for img in self.list_images())

    def move_to(self, naming: str, output_folder: Path) -> None:
        output = output_folder / (naming + self.archive.EXTENSION)
        if output.exists():
            LOGGER.warning("'%s' already exists, skipping", output)
            return

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.filepath, output)
        self._archive = Archive.load(filepath=output)
