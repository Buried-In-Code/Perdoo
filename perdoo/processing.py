__all__ = ["ProcessingPlan"]

from dataclasses import dataclass
from pathlib import Path

from perdoo.comic import Comic
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.settings import Naming, Output

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11


def generate_naming(
    settings: Naming, metadata: tuple[MetronInfo | None, ComicInfo | None]
) -> str | None:
    filepath = None
    if metadata[0]:
        filepath = metadata[0].get_filename(settings=settings)
    if not filepath and metadata[1]:
        filepath = metadata[1].get_filename(settings=settings)
    return filepath.lstrip("/") if filepath else None


@dataclass
class ProcessingPlan:
    comic: Comic
    metroninfo: MetronInfo | None
    comicinfo: ComicInfo | None
    write_metron: bool
    write_comic: bool
    remove_extras: list[Path]
    rename_images: bool
    naming: str | None

    @classmethod
    def build(
        cls,
        entry: Comic,
        metroninfo: MetronInfo | None,
        comicinfo: ComicInfo | None,
        settings: Output,
        skip_clean: bool,
        skip_rename: bool,
    ) -> Self:
        local_metron, local_comic = entry.read_metadata()
        write_metron = local_metron != metroninfo
        write_comic = local_comic != comicinfo

        extras = entry.list_extras() if not skip_clean else []

        naming = None
        rename_images = False
        if not skip_rename:
            naming = generate_naming(settings.naming, (metroninfo, comicinfo))
            rename_images = bool(naming and not entry.validate_naming(naming))
        return cls(
            comic=entry,
            metroninfo=metroninfo,
            comicinfo=comicinfo,
            write_metron=write_metron,
            write_comic=write_comic,
            remove_extras=extras,
            rename_images=rename_images,
            naming=naming,
        )

    def apply(self) -> None:
        if not (self.write_metron or self.write_comic or self.remove_extras or self.rename_images):
            return

        with self.comic.open_session() as session:
            if self.write_metron:
                if self.metroninfo:
                    session.write(MetronInfo.FILENAME, self.metroninfo.to_bytes())
                else:
                    session.remove(MetronInfo.FILENAME)

            if self.write_comic:
                if self.comicinfo:
                    session.write(ComicInfo.FILENAME, self.comicinfo.to_bytes())
                else:
                    session.remove(ComicInfo.FILENAME)

            for extra in self.remove_extras:
                session.remove(extra.name)

            if self.rename_images and self.naming:
                images = self.comic.list_images()
                stem = Path(self.naming).stem
                pad = len(str(len(images)))
                for idx, img in enumerate(images):
                    new_name = f"{stem}_{str(idx).zfill(pad)}{img.suffix}"
                    if img.name != new_name:
                        session.rename(img.name, new_name)
