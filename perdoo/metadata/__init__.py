__all__ = ["ComicInfo", "MetronInfo", "get_metadata"]

import logging
from typing import cast

from pydantic import ValidationError

from perdoo.archives import BaseArchive
from perdoo.metadata._base import PascalModel
from perdoo.metadata.comic_info import ComicInfo
from perdoo.metadata.metron_info import MetronInfo

LOGGER = logging.getLogger("perdoo.models")


def get_metadata(
    archive: BaseArchive, debug: bool = False
) -> tuple[MetronInfo | None, ComicInfo | None]:
    filenames = archive.list_filenames()

    def read_meta_file(cls: type[PascalModel], filename: str) -> PascalModel | None:
        if filename in filenames:
            return cls.from_bytes(content=archive.read_file(filename=filename))
        return None

    metron_info = None
    try:
        metron_info = read_meta_file(cls=MetronInfo, filename="MetronInfo.xml") or read_meta_file(
            cls=MetronInfo, filename="/MetronInfo.xml"
        )
        if metron_info:
            metron_info = cast(MetronInfo, metron_info)
    except ValidationError as ve:
        if debug:
            LOGGER.error("'%s' contains an invalid MetronInfo file: %s", archive.path.name, ve)  # noqa: TRY400
        else:
            LOGGER.error("'%s' contains an invalid MetronInfo file", archive.path.name)  # noqa: TRY400
    comic_info = None
    try:
        comic_info = read_meta_file(cls=ComicInfo, filename="ComicInfo.xml") or read_meta_file(
            cls=ComicInfo, filename="/ComicInfo.xml"
        )
        if comic_info:
            comic_info = cast(ComicInfo, comic_info)
    except ValidationError as ve:
        if debug:
            LOGGER.error("'%s' contains an invalid ComicInfo file: %s", archive.path.name, ve)  # noqa: TRY400
        else:
            LOGGER.error("'%s' contains an invalid ComicInfo file", archive.path.name)  # noqa: TRY400
    return metron_info, comic_info
