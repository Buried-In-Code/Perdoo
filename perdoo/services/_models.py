__all__ = [
    "Ids",
    "MetadataResult",
    "Query",
    "get_comic_info_note_id",
    "get_comic_info_note_modified",
    "query_from_comic_info",
    "query_from_filename",
    "query_from_metron_info",
    "set_comic_info_note_id",
]

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property

from comicfn2dict import comicfn2dict
from shortbox import Comic
from shortbox.errors import MissingArchiveMemberError
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Id, InformationSource

from perdoo import __version__
from perdoo.console import CONSOLE
from perdoo.phash import phash
from perdoo.settings import Service

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
class Ids:
    series: int | None = None
    issue: int | None = None


def _no_cover() -> str | None:
    return None


@dataclass
class Query:
    filename: str
    name: str
    number: str | None = None
    volume: int | None = None
    year: int | None = None
    ids: dict[Service, Ids] = field(default_factory=dict)
    cover_source: Callable[[], str | None] = field(default=_no_cover, repr=False)
    announced: bool = field(default=False, repr=False)

    def ids_for(self, service: Service) -> Ids:
        return self.ids.setdefault(service, Ids())

    @cached_property
    def cover_hash(self) -> str | None:
        return self.cover_source()

    @staticmethod
    def build(comic: Comic, sources: Mapping[InformationSource, Service]) -> "Query":
        if (
            (metron_info := comic.get_metadata(MetronInfo))
            and metron_info.series
            and metron_info.series.name
        ):
            query = query_from_metron_info(metron_info, comic.file.stem, sources)
        elif (comic_info := comic.get_metadata(ComicInfo)) and comic_info.series:
            query = query_from_comic_info(comic_info, comic.file.stem, sources)
        else:
            query = query_from_filename(comic.file.stem)
        query.cover_source = lambda: _get_cover_hash(comic=comic)
        return query


def _get_cover_hash(comic: Comic) -> str | None:
    try:
        return phash(comic.get_cover())
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


def query_from_metron_info(
    metadata: MetronInfo, filename: str, sources: Mapping[InformationSource, Service]
) -> Query:
    query = Query(
        filename=filename,
        name=metadata.series.name,
        number=metadata.number,
        volume=metadata.series.volume,
        year=metadata.series.start_year,
    )
    for source, service in sources.items():
        if issue_id := get_id(metadata.ids, source):
            query.ids_for(service).issue = int(issue_id)
    primary = next((x.source for x in metadata.ids if x.primary), None)
    if (series_id := metadata.series.id) and primary and (service := sources.get(primary)):
        query.ids_for(service).series = int(series_id)
    return query


def query_from_comic_info(
    metadata: ComicInfo, filename: str, sources: Mapping[InformationSource, Service]
) -> Query:
    volume = metadata.volume
    year = volume if volume and volume > 1900 else None
    volume = volume if volume and volume < 1900 else None
    query = Query(
        filename=filename,
        name=metadata.series or filename,
        number=metadata.number,
        volume=volume,
        year=year,
    )
    for source, service in sources.items():
        if issue_id := get_comic_info_note_id(metadata.notes, source):
            query.ids_for(service).issue = issue_id
    return query


def query_from_filename(filename: str) -> Query:
    series_name = comicfn2dict(filename).get("series", filename)
    return Query(filename=filename, name=str(series_name).replace("-", " "))
