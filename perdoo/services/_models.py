__all__ = [
    "MetadataResult",
    "Search",
    "get_comic_info_note_id",
    "get_comic_info_note_modified",
    "set_comic_info_note_id",
]

import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

from comicfn2dict import comicfn2dict
from imagehash import phash
from PIL import Image
from shortbox import Comic
from shortbox.errors import MissingArchiveMemberError
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Id, InformationSource

from perdoo import __version__
from perdoo.console import CONSOLE

_PERDOO_NOTE = re.compile(
    r"^Tagged with Perdoo v\S+ using info from (?P<source>.+?) at (?P<modified>.+?)\. \[issue_id:(?P<id>\d+)\]$",  # noqa: E501
    flags=re.IGNORECASE,
)
_METRON_TAGGER_NOTE = re.compile(
    r"^Tagged with MetronTagger-\S+ using info from Metron on (?P<modified>.+?)\. \[issue_id:(?P<id>\d+)\]$",  # noqa: E501
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class MetadataResult:
    comic_info: ComicInfo
    metron_info: MetronInfo


@dataclass
class SeriesSearch:
    name: str
    volume: int | None = None
    year: int | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class IssueSearch:
    number: str | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class Search:
    series: SeriesSearch
    issue: IssueSearch
    filename: str
    cover_hash: str | None = None

    @staticmethod
    def build(comic: Comic) -> "Search":
        search: Search
        if (
            (metron_info := comic.get_metadata(MetronInfo))
            and metron_info.series
            and metron_info.series.name
        ):
            search = search_from_metron_info(metadata=metron_info, filename=comic.file.stem)
        elif (comic_info := comic.get_metadata(ComicInfo)) and comic_info.series:
            search = search_from_comic_info(metadata=comic_info, filename=comic.file.stem)
        else:
            search = search_from_filename(filename=comic.file.stem)
        search.cover_hash = _get_cover_hash(comic=comic)
        return search


def _get_cover_hash(comic: Comic) -> str | None:
    try:
        with Image.open(BytesIO(comic.get_cover())) as cover:
            return str(phash(cover))
    except (MissingArchiveMemberError, OSError) as err:
        CONSOLE.print(
            f"Unable to generate a cover hash for {comic.file.name!r}: {err}",
            style="logging.level.warning",
        )
        return None


def get_id(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source is source), None)


def get_comic_info_note_id(notes: str | None, source: InformationSource) -> int | None:
    if not notes:
        return None
    source_str = source.value.casefold()
    if (match := _PERDOO_NOTE.match(notes)) and source_str == match["source"].casefold():
        return int(match["id"])
    if (match := _METRON_TAGGER_NOTE.match(notes)) and source == InformationSource.METRON:
        return int(match["id"])
    if (
        "ComicTagger".casefold() in notes.casefold()
        and source_str in notes.casefold()
        and (match := re.search(r"issue id (\d+)|cvdb(\d+)", notes.lower()))
    ):
        return int(match.group(1) or match.group(2))
    return None


def get_comic_info_note_modified(notes: str | None) -> datetime | None:
    if not notes:
        return None
    if match := _PERDOO_NOTE.match(notes):
        try:
            return datetime.fromisoformat(match["modified"])
        except ValueError:
            return None
    if match := _METRON_TAGGER_NOTE.match(notes):
        try:
            return datetime.strptime(match["modified"], "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007
        except ValueError:
            return None
    return None


def set_comic_info_note_id(
    comic_info: ComicInfo, source: InformationSource, value: int, modified: datetime | None = None
) -> None:
    modified = modified or datetime.now().astimezone()
    comic_info.notes = f"Tagged with Perdoo v{__version__} using info from {source.value} at {modified.isoformat()}. [issue_id:{value}]"  # noqa: E501


def search_from_metron_info(metadata: MetronInfo, filename: str) -> Search:
    series_id = metadata.series.id
    comicvine_id = get_id(metadata.ids, InformationSource.COMIC_VINE)
    metron_id = get_id(metadata.ids, InformationSource.METRON)
    source = next((x.source for x in metadata.ids if x.primary), None)
    return Search(
        series=SeriesSearch(
            name=metadata.series.name,
            volume=metadata.series.volume,
            year=metadata.series.start_year,
            comicvine=int(series_id)
            if series_id and source == InformationSource.COMIC_VINE
            else None,
            metron=int(series_id) if series_id and source == InformationSource.METRON else None,
        ),
        issue=IssueSearch(
            number=metadata.number,
            comicvine=int(comicvine_id) if comicvine_id else None,
            metron=int(metron_id) if metron_id else None,
        ),
        filename=filename,
    )


def search_from_comic_info(metadata: ComicInfo, filename: str) -> Search:
    volume = metadata.volume
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    return Search(
        series=SeriesSearch(name=metadata.series or filename, volume=volume, year=year),
        issue=IssueSearch(
            number=metadata.number,
            comicvine=get_comic_info_note_id(metadata.notes, InformationSource.COMIC_VINE),
            metron=get_comic_info_note_id(metadata.notes, InformationSource.METRON),
        ),
        filename=filename,
    )


def search_from_filename(filename: str) -> Search:
    series_name = comicfn2dict(filename).get("series", filename)
    series_name = str(series_name).replace("-", " ")
    return Search(series=SeriesSearch(name=series_name), issue=IssueSearch(), filename=filename)
