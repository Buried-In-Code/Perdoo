__all__ = ["Metron"]

import time
from collections.abc import Callable, Sequence
from datetime import datetime
from functools import wraps
from math import ceil
from typing import Self, TypeVar

from imagehash import hex_to_hash
from mokkari.exceptions import ApiError, RateLimitError
from mokkari.rate_limit import HeaderPacedRateLimiter
from mokkari.schemas.issue import BaseIssue, Issue
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from natsort import humansorted, ns
from shortbox.metadata import ComicInfo, MetronInfo, comic_info as ci, metron_info as mi
from shortbox.metadata.metron_info import Format, InformationSource

from perdoo import get_cache_home
from perdoo.console import CONSOLE
from perdoo.services._models import MetadataResult, Query, set_comic_info_note_id
from perdoo.services._provider import Candidate, IssueQuery, Provider, ProviderError, SeriesQuery
from perdoo.settings import Service, Settings

T = TypeVar("T")


def rate_limit_retry(max_retries: int = 5) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:  # noqa: ANN002, ANN003
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as err:
                    if attempt == max_retries - 1:
                        raise
                    CONSOLE.print(
                        f"Rate limited, waiting {ceil(err.retry_after)} seconds...",
                        style="logging.level.warning",
                    )
                    time.sleep(ceil(err.retry_after))
            raise AssertionError("Unreachable")

        return wrapper

    return decorator


@rate_limit_retry()
def _request(method: Callable[..., T], *args, **kwargs) -> T:  # noqa: ANN002, ANN003
    try:
        return method(*args, **kwargs)
    except ApiError as err:
        raise ProviderError(str(err)) from err


class Metron(Provider[Series, Issue]):
    service = Service.METRON
    source = InformationSource.METRON
    series_filters = ("year", "volume")

    def __init__(self, token: str, cover_hash_distance: int = 10) -> None:
        cache = SqliteCache(db_name=str(get_cache_home() / "mokkari.sqlite"))
        rate_limiter = HeaderPacedRateLimiter()
        self._session = Mokkari(api_token=token, cache=cache, rate_limiter=rate_limiter)
        self._cover_hash_distance = cover_hash_distance

    @classmethod
    def from_settings(cls, settings: Settings) -> Self | None:
        if not (token := settings.services.metron.token):
            return None
        return cls(token=token, cover_hash_distance=settings.sync.cover_hash_distance)

    def find_series(self, query: SeriesQuery) -> Sequence[Candidate]:
        params = {"name": query.name, "volume": query.volume, "year_began": query.year}
        series = sorted(
            _request(self._session.series_list, params=params),
            key=lambda x: (x.display_name, x.volume),
        )
        return [
            Candidate(
                id=x.id,
                title=f"{x.display_name} v{x.volume}",
                url=f"https://metron.cloud/series/{x.id}",
            )
            for x in series
        ]

    def find_issues(self, query: IssueQuery) -> Sequence[Candidate]:
        params = {"series_id": query.series_id, "number": query.number}
        issues = humansorted(
            _request(self._session.issues_list, params=params),
            key=lambda x: (x.number, x.issue_name),
            alg=ns.NA | ns.G,
        )
        return [self._candidate(x) for x in issues]

    def get_series(self, series_id: int) -> Series:
        if not (series := _request(self._session.series, _id=series_id)):
            raise ProviderError(f"Series {series_id} was not found on Metron")
        return series

    def get_issue(self, issue_id: int) -> Issue:
        if not (issue := _request(self._session.issue, _id=issue_id)):
            raise ProviderError(f"Issue {issue_id} was not found on Metron")
        return issue

    def series_id_of(self, issue: Issue) -> int:
        return issue.series.id

    def build(self, series: Series, issue: Issue, format_: Format | None) -> MetadataResult:  # noqa: ARG002
        return MetadataResult(
            comic_info=_comic_info(series=series, issue=issue),
            metron_info=_metron_info(series=series, issue=issue),
        )

    def lookup_series(self, query: Query) -> int | None:
        if not (comicvine_id := query.ids_for(Service.COMICVINE).series):
            return None
        series = _request(self._session.series_list, params={"cv_id": comicvine_id})
        return series[0].id if series else None

    def lookup_issue(self, query: Query) -> int | None:
        if not (comicvine_id := query.ids_for(Service.COMICVINE).issue):
            return None
        issues = _request(self._session.issues_list, params={"cv_id": comicvine_id})
        return issues[0].id if issues else None

    def find_by_cover(self, query: Query) -> Sequence[Candidate]:
        if not query.cover_hash:
            return ()
        source_hash = hex_to_hash(hexstr=query.cover_hash)
        issues = _request(self._session.issues_list, params={"cover_hash": query.cover_hash})
        return [
            self._candidate(x)
            for x in issues
            if source_hash - hex_to_hash(hexstr=x.cover_hash) <= self._cover_hash_distance
        ]

    @staticmethod
    def _candidate(issue: BaseIssue) -> Candidate:
        return Candidate(
            id=issue.id, title=issue.issue_name, url=f"https://metron.cloud/issues/{issue.id}"
        )


def _metron_info(series: Series, issue: Issue) -> MetronInfo:
    def load_role(value: str) -> mi.Role:
        try:
            return mi.Role.load(value=value.strip())
        except ValueError:
            return mi.Role.OTHER

    ids = [mi.Id(primary=True, source=InformationSource.METRON, value=str(issue.id))]
    if issue.cv_id:
        ids.append(mi.Id(source=InformationSource.COMIC_VINE, value=str(issue.cv_id)))
    if issue.gcd_id:
        ids.append(mi.Id(source=InformationSource.GRAND_COMICS_DATABASE, value=str(issue.gcd_id)))
    return MetronInfo(
        ids=ids,
        publisher=mi.Publisher(
            id=str(series.publisher.id),
            name=series.publisher.name,
            imprint=mi.Resource[str](id=str(series.imprint.id), value=series.imprint.name)
            if series.imprint
            else None,
        ),
        series=mi.Series(
            id=str(series.id),
            name=series.name,
            sort_name=series.sort_name,
            volume=series.volume,
            format=mi.Format.load(value=series.series_type.name),
            start_year=series.year_began,
            alternative_names=[],
        ),
        collection_title=issue.collection_title or None,
        number=issue.number,
        stories=[mi.Resource[str](value=x) for x in issue.story_titles],
        summary=issue.desc,
        prices=[mi.Price(country="US", value=issue.price)] if issue.price else [],
        cover_date=issue.cover_date,
        store_date=issue.store_date,
        page_count=issue.page_count or 0,
        genres=[mi.Resource[str](id=str(x.id), value=x.name) for x in issue.series.genres],
        arcs=[mi.Arc(id=str(x.id), name=x.name) for x in issue.arcs],
        characters=[mi.Resource[str](id=str(x.id), value=x.name) for x in issue.characters],
        teams=[mi.Resource[str](id=str(x.id), value=x.name) for x in issue.teams],
        universes=[mi.Universe(id=str(x.id), name=x.name) for x in issue.universes],
        gtin=mi.GTIN(isbn=issue.isbn or None, upc=issue.upc or None)
        if issue.isbn or issue.upc
        else None,
        age_rating=mi.AgeRating.load(value=issue.rating.name),
        reprints=[mi.Resource[str](id=str(x.id), value=x.issue) for x in issue.reprints],
        urls=[mi.Url(primary=True, value=str(issue.resource_url))],
        credits=[
            mi.Credit(
                creator=mi.Resource[str](id=str(x.id), value=x.creator),
                roles=[
                    mi.Resource[mi.Role](id=str(r.id), value=load_role(value=r.name))
                    for r in x.role
                ],
            )
            for x in issue.credits
        ],
        last_modified=datetime.now().astimezone(),
        locations=[],
        tags=[],
    )


def _comic_info(series: Series, issue: Issue) -> ComicInfo:
    def load_age_rating(value: str) -> ci.AgeRating:
        try:
            return ci.AgeRating.load(value=value.strip())
        except ValueError:
            return ci.AgeRating.UNKNOWN

    comic_info = ComicInfo(
        title=issue.collection_title,
        series=series.name,
        number=issue.number,
        volume=series.volume,
        summary=issue.desc,
        publisher=series.publisher.name,
        web=str(issue.resource_url),
        page_count=issue.page_count or 0,
        format=series.series_type.name,
        age_rating=load_age_rating(value=issue.rating.name),
        pages=[],
    )

    comic_info.cover_date = issue.cover_date
    comic_info.credits = {x.creator: [r.name for r in x.role] for x in issue.credits}
    comic_info.genre_list = [x.name for x in series.genres]
    comic_info.character_list = [x.name for x in issue.characters]
    comic_info.team_list = [x.name for x in issue.teams]
    comic_info.story_arc_list = [x.name for x in issue.arcs]
    set_comic_info_note_id(comic_info, source=InformationSource.METRON, value=issue.id)

    return comic_info
