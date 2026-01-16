__all__ = ["IMAGE_EXTENSIONS", "Comic"]

import logging
import shutil
from pathlib import Path
from typing import Final, Literal

from natsort import humansorted, ns

from perdoo.comic.archive import Archive, CBZArchive
from perdoo.comic.metadata import ComicInfo, Metadata, MetronInfo
from perdoo.settings import Naming

LOGGER = logging.getLogger(__name__)
METADATA_FILENAMES: Final[frozenset[str]] = frozenset(["ComicInfo.xml", "MetronInfo.xml"])
IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset([".png", ".jpg", ".jpeg", ".webp", ".jxl"])


class Comic:
    def __init__(self, filepath: Path):
        self._archive: Archive = Archive.load(filepath=filepath)
        self._metadata: dict[str, Metadata | None] = {}
        self._load_metadata()

    @property
    def archive(self) -> Archive:
        return self._archive

    @property
    def filepath(self) -> Path:
        return self.archive.filepath

    @property
    def comic_info(self) -> ComicInfo | None:
        return self._metadata.get("ComicInfo")

    @property
    def metron_info(self) -> MetronInfo | None:
        return self._metadata.get("MetronInfo")

    def _load_metadata(self) -> None:
        if self.archive.exists(filename="ComicInfo.xml"):
            self._metadata["ComicInfo"] = ComicInfo.from_bytes(
                content=self.archive.read_file(filename="ComicInfo.xml")
            )
        if self.archive.exists(filename="MetronInfo.xml"):
            self._metadata["MetronInfo"] = MetronInfo.from_bytes(
                content=self.archive.read_file(filename="MetronInfo.xml")
            )

    def convert_to(self, extension: Literal["cbz"]) -> None:
        cls = {"cbz": CBZArchive}[extension]
        if not isinstance(self.archive, cls):
            self._archive = cls.convert_from(old_archive=self.archive)

    def clean_archive(self) -> None:
        for filename in self.archive.list_filenames():
            filepath = Path(filename)
            if (
                filepath.name not in METADATA_FILENAMES
                and filepath.suffix.lower() not in IMAGE_EXTENSIONS
            ):
                self.archive.remove_file(filename=filename)
                LOGGER.info("Removed '%s' from '%s'", filename, self.filepath.name)

    def write_metadata(self, metadata: Metadata) -> None:
        if isinstance(metadata, ComicInfo):
            self.archive.write_file(filename="ComicInfo.xml", data=metadata.to_bytes())
            self._metadata["ComicInfo"] = metadata
        if isinstance(metadata, MetronInfo):
            self.archive.write_file(filename="MetronInfo.xml", data=metadata.to_bytes())
            self._metadata["MetronInfo"] = metadata

    def _get_filepath_from_metadata(self, naming: Naming) -> str | None:
        if self.metron_info:
            return self.metron_info.get_filename(settings=naming)
        if self.comic_info:
            return self.comic_info.get_filename(settings=naming)
        return None

    def _rename_images(self, base_name: str) -> None:
        files = [
            x for x in self.archive.list_filenames() if Path(x).suffix.lower() in IMAGE_EXTENSIONS
        ]
        if all(x.startswith(base_name) for x in files):
            return
        files = humansorted(files, alg=ns.NA | ns.G | ns.P)
        pad_count = len(str(len(files))) if files else 1
        for idx, filename in enumerate(files):
            img_file = Path(filename)
            new_file = img_file.with_stem(f"{base_name}_{str(idx).zfill(pad_count)}")
            if new_file.stem != img_file.stem:
                LOGGER.info("Renaming '%s' to '%s'", img_file.name, new_file.name)
                file_contents = self.archive.read_file(filename=filename)
                self.archive.remove_file(filename=filename)
                self.archive.write_file(filename=new_file.name, data=file_contents)

    def rename(self, naming: Naming, output_folder: Path) -> None:
        new_filepath = self._get_filepath_from_metadata(naming=naming)
        if new_filepath is None:
            LOGGER.warning("Not enough information to rename '%s', skipping", self.filepath.name)
            return
        new_filepath = new_filepath.lstrip("/")

        output = output_folder / f"{new_filepath}.cbz"
        self._rename_images(base_name=output.stem)
        if output.relative_to(output_folder) == self.filepath.resolve().relative_to(output_folder):
            return
        if output.exists():
            LOGGER.warning("'%s' already exists, skipping", output.relative_to(output_folder))
            return
        output.parent.mkdir(parents=True, exist_ok=True)

        LOGGER.info(
            "Renaming '%s' to '%s'", self.filepath.name, output.relative_to(output_folder.parent)
        )
        shutil.move(self.filepath, output)
        self._archive = Archive.load(filepath=output)
