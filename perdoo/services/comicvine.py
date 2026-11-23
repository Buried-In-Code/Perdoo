__all__ = ["Comicvine"]

import re
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Self, TypeVar

from natsort import humansorted, ns
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import (
    Arc,
    Credit,
    Format,
    Id,
    InformationSource,
    Publisher,
    Resource,
    Role,
    Series,
    Url,
)
from simyan.comicvine import Comicvine as Simyan
from simyan.errors import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume

from perdoo import get_cache_home
from perdoo.services._models import MetadataResult, set_comic_info_note_id
from perdoo.services._provider import Candidate, IssueQuery, Provider, ProviderError, SeriesQuery
from perdoo.settings import Service, Settings

T = TypeVar("T")


def _request(method: Callable[..., T], *args, **kwargs) -> T:  # noqa: ANN002, ANN003
    try:
        return method(*args, **kwargs)
    except ServiceError as err:
        raise ProviderError(str(err)) from err


class Comicvine(Provider[Volume, Issue]):
    service = Service.COMICVINE
    source = InformationSource.COMIC_VINE
    series_noun = "Volume"
    series_filters = (("year", "StartYear"),)
    issue_filters = (("number", "IssueNumber"),)
    provides_format = False

    def __init__(self, api_key: str) -> None:
        self._session = Simyan(
            api_key=api_key,
            cache_path=get_cache_home() / "simyan.sqlite",
            ratelimit_path=get_cache_home() / "simyan-rates.sqlite",
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> Self | None:
        if not (api_key := settings.services.comicvine.api_key):
            return None
        return cls(api_key=api_key)

    def find_series(self, query: SeriesQuery) -> Sequence[Candidate]:
        volumes = sorted(
            _request(self._session.list_volumes, {"filter": f"name:{query.name}"}),
            key=lambda x: (
                x.publisher.name if x.publisher and x.publisher.name else "",
                x.name,
                x.start_year or 0,
            ),
        )
        return [
            Candidate(
                id=x.id,
                title=f"{x.name} ({x.start_year})",
                url=f"https://comicvine.gamespot.com/volumes/4050-{x.id}",
                detail=x.publisher.name if x.publisher and x.publisher.name else "",
            )
            for x in volumes
            if not query.year or x.start_year == query.year
        ]

    def find_issues(self, query: IssueQuery) -> Sequence[Candidate]:
        filter_ = f"volume:{query.series_id}"
        if query.number:
            filter_ += f",issue_number:{query.number}"
        issues = humansorted(
            _request(self._session.list_issues, {"filter": filter_}),
            key=lambda x: (x.number, x.name),
            alg=ns.NA | ns.G,
        )
        return [
            Candidate(
                id=x.id,
                title=f"{x.number} - {x.name or ''}",
                url=f"https://comicvine.gamespot.com/issues/4000-{x.id}",
            )
            for x in issues
        ]

    def get_series(self, series_id: int) -> Volume:
        return _request(self._session.get_volume, volume_id=series_id)

    def get_issue(self, issue_id: int) -> Issue:
        return _request(self._session.get_issue, issue_id=issue_id)

    def series_id_of(self, issue: Issue) -> int:
        return issue.volume.id

    def build(self, series: Volume, issue: Issue, format_: Format | None) -> MetadataResult:
        return MetadataResult(
            comic_info=_comic_info(series=series, issue=issue, format_=format_),
            metron_info=_metron_info(series=series, issue=issue, format_=format_),
        )


def _metron_info(series: Volume, issue: Issue, format_: Format | None) -> MetronInfo:
    def load_role(value: str) -> Role:
        try:
            return Role.load(value=value.strip())
        except ValueError:
            return Role.OTHER

    return MetronInfo(
        arcs=[Arc(id=str(x.id), name=x.name) for x in issue.story_arcs if x.name],
        characters=[Resource[str](id=str(x.id), value=x.name) for x in issue.characters if x.name],
        collection_title=issue.name,
        cover_date=issue.cover_date,
        credits=[
            Credit(
                creator=Resource[str](id=str(x.id), value=x.name),
                roles=[
                    Resource[Role](value=load_role(value=r.strip()))
                    for r in re.split(r"[~\r\n,]+", x.roles)
                    if r.strip()
                ],
            )
            for x in issue.creators
            if x.name
        ],
        genres=[],
        ids=[Id(primary=True, source=InformationSource.COMIC_VINE, value=str(issue.id))],
        last_modified=datetime.now().astimezone(),
        locations=[Resource[str](id=str(x.id), value=x.name) for x in issue.locations if x.name],
        number=issue.number,
        prices=[],
        publisher=Publisher(id=str(series.publisher.id), name=series.publisher.name)
        if series.publisher and series.publisher.name
        else None,
        reprints=[],
        series=Series(
            alternative_names=[],
            format=format_,
            id=str(series.id),
            name=series.name,
            start_year=series.start_year,
        ),
        store_date=issue.store_date,
        stories=[],
        summary=issue.summary,
        tags=[],
        teams=[Resource[str](id=str(x.id), value=x.name) for x in issue.teams if x.name],
        universes=[],
        urls=[Url(primary=True, value=str(issue.site_url))],
    )


def _comic_info(series: Volume, issue: Issue, format_: Format | None) -> ComicInfo:
    comic_info = ComicInfo(
        format=str(format_) if format_ else None,
        number=issue.number,
        pages=[],
        publisher=series.publisher.name if series.publisher else None,
        series=series.name,
        summary=issue.summary,
        title=issue.name,
        web=str(issue.site_url),
    )

    comic_info.cover_date = issue.cover_date
    comic_info.credits = {
        x.name: [r.strip() for r in re.split(r"[~\r\n,]+", x.roles) if r.strip()]
        for x in issue.creators
        if x.name
    }
    comic_info.character_list = [x.name for x in issue.characters if x.name]
    comic_info.team_list = [x.name for x in issue.teams if x.name]
    comic_info.location_list = [x.name for x in issue.locations if x.name]
    comic_info.story_arc_list = [x.name for x in issue.story_arcs if x.name]
    set_comic_info_note_id(comic_info, source=InformationSource.COMIC_VINE, value=issue.id)

    return comic_info
