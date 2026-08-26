__all__ = ["Metron"]

import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from math import ceil
from typing import TypeVar

from comic_archive.metadata import ComicInfo, MetronInfo
from comic_archive.metadata.metron_info import InformationSource
from mokkari.exceptions import ApiError, RateLimitError
from mokkari.schemas.issue import Issue
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from natsort import humansorted, ns
from questionary import Choice, confirm, text

from perdoo import get_cache_home
from perdoo.console import CONSOLE
from perdoo.services._base import prompt_select
from perdoo.services._models import IssueSearch, MetadataResult, Search, SeriesSearch

T = TypeVar("T")


def rate_limit_retry(max_retries: int = 5) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:  # noqa: ANN002, ANN003
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as err:  # noqa: PERF203
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


class Metron:
    def __init__(self, token: str):
        cache = SqliteCache(db_name=str(get_cache_home() / "mokkari.sqlite"))
        self.session = Mokkari(api_token=token, cache=cache)

    @rate_limit_retry()
    def _search_series_by_comicvine(self, comicvine_id: int | None) -> int | None:
        if not comicvine_id:
            return None
        try:
            series = self.session.series_list(params={"cv_id": comicvine_id})
            if series and len(series) >= 1:
                return series[0].id
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    @rate_limit_retry()
    def _search_series(
        self, name: str | None, volume: int | None, year: int | None, filename: str
    ) -> int | None:
        name = name or text(message="Series Name").ask()
        try:
            options = sorted(
                self.session.series_list(
                    params={"name": name, "volume": volume, "year_began": year}  # ty: ignore[invalid-argument-type]
                ),
                key=lambda x: (x.display_name, x.volume),
            )
            if options:
                search = name
                if volume:
                    search += f" v{volume}"
                if year:
                    search += f" ({year})"
                choices = [
                    Choice(
                        title=[
                            ("class:dim", f"{x.id} | "),
                            ("class:title", f"{x.display_name} v{x.volume}"),
                        ],
                        description=f"https://metron.cloud/series/{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                selected = prompt_select(
                    message=f"Searching Metron for Series matching {filename!r}"
                    if not year
                    else f"Searching Metron for Series {search!r}",
                    choices=choices,
                )
                if selected:
                    return selected.id
            else:
                CONSOLE.print(
                    f"Unable to find any Series on Metron for the file: {filename!r}",
                    style="logging.level.warning",
                )
            if year:
                CONSOLE.print("Searching again without the YearBegan", style="logging.level.info")
                return self._search_series(name=name, volume=volume, year=None, filename=filename)
            if volume:
                CONSOLE.print("Searching again without the Volume", style="logging.level.info")
                return self._search_series(name=name, volume=None, year=None, filename=filename)
            if confirm(message="Search Again", default=False).ask():
                return self._search_series(name=None, volume=None, year=None, filename=filename)
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    @rate_limit_retry()
    def _fetch_series(self, search: SeriesSearch, filename: str) -> Series | None:
        series_id = (
            search.metron
            or self._search_series_by_comicvine(comicvine_id=search.comicvine)
            or self._search_series(
                name=search.name, volume=search.volume, year=search.year, filename=filename
            )
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            search.metron = series_id
            return series
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        if search.metron:
            search.metron = None
            return self._fetch_series(search=search, filename=filename)
        return None

    @rate_limit_retry()
    def _search_issue_by_comicvine(self, comicvine_id: int | None) -> int | None:
        if not comicvine_id:
            return None
        try:
            issues = self.session.issues_list(params={"cv_id": comicvine_id})
            if issues and len(issues) >= 1:
                return issues[0].id
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    @rate_limit_retry()
    def _search_issue(self, series_id: int, number: str | None, filename: str) -> int | None:
        try:
            options = humansorted(
                self.session.issues_list(params={"series_id": series_id, "number": number}),  # ty: ignore[invalid-argument-type]
                key=lambda x: (x.number, x.issue_name),
                alg=ns.NA | ns.G,
            )
            if options:
                choices = [
                    Choice(
                        title=[("class:dim", f"{x.id} | "), ("class:title", x.issue_name)],
                        description=f"https://metron.cloud/issues/{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                selected = prompt_select(
                    message=f"Searching Metron for Issues matching {filename!r}"
                    if not number
                    else f"Searching Metron for Issues with number {number!r}",
                    choices=choices,
                )
                if selected:
                    return selected.id
            else:
                CONSOLE.print(
                    f"Unable to find any Comics on Metron for the file: {filename!r}",
                    style="logging.level.warning",
                )
            if number:
                CONSOLE.print("Searching again without the Number", style="logging.level.info")
                return self._search_issue(series_id=series_id, number=None, filename=filename)
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        return None

    @rate_limit_retry()
    def _fetch_issue(self, series_id: int, search: IssueSearch, filename: str) -> Issue | None:
        issue_id = (
            search.metron
            or self._search_issue_by_comicvine(comicvine_id=search.comicvine)
            or self._search_issue(series_id=series_id, number=search.number, filename=filename)
        )
        if not issue_id:
            return None
        try:
            issue = self.session.issue(_id=issue_id)
            search.metron = issue_id
            return issue
        except ApiError as err:
            CONSOLE.print(err, style="logging.level.error")
        if search.metron:
            search.metron = None
            return self._fetch_issue(series_id=series_id, search=search, filename=filename)
        return None

    def _build_metron_info(self, series: Series, issue: Issue) -> MetronInfo:
        from comic_archive.metadata.metron_info import (  # noqa: PLC0415
            GTIN,
            AgeRating,
            Arc,
            Credit,
            Format,
            Id,
            Price,
            Publisher,
            Resource,
            Role,
            Series,
            Universe,
            Url,
        )

        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        ids = [Id(primary=True, source=InformationSource.METRON, value=str(issue.id))]
        if issue.cv_id:
            ids.append(Id(source=InformationSource.COMIC_VINE, value=str(issue.cv_id)))
        if issue.gcd_id:
            ids.append(Id(source=InformationSource.GRAND_COMICS_DATABASE, value=str(issue.gcd_id)))
        return MetronInfo(
            ids=ids,
            publisher=Publisher(
                id=str(series.publisher.id),
                name=series.publisher.name,
                imprint=Resource[str](id=str(series.imprint.id), value=series.imprint.name)
                if series.imprint
                else None,
            ),
            series=Series(
                id=str(series.id),
                name=series.name,
                sort_name=series.sort_name,
                volume=series.volume,
                format=Format.load(value=series.series_type.name),
                start_year=series.year_began,
                alternative_names=[],
            ),
            collection_title=issue.collection_title or None,
            number=issue.number,
            stories=[Resource[str](value=x) for x in issue.story_titles],
            summary=issue.desc,
            prices=[Price(country="US", value=issue.price)] if issue.price else [],
            cover_date=issue.cover_date,
            store_date=issue.store_date,
            page_count=issue.page_count or 0,
            genres=[Resource[str](id=str(x.id), value=x.name) for x in issue.series.genres],
            arcs=[Arc(id=str(x.id), name=x.name) for x in issue.arcs],
            characters=[Resource[str](id=str(x.id), value=x.name) for x in issue.characters],
            teams=[Resource[str](id=str(x.id), value=x.name) for x in issue.teams],
            universes=[Universe(id=str(x.id), name=x.name) for x in issue.universes],
            gtin=GTIN(isbn=issue.isbn or None, upc=issue.upc or None)
            if issue.isbn or issue.upc
            else None,
            age_rating=AgeRating.load(value=issue.rating.name),
            reprints=[Resource[str](id=str(x.id), value=x.issue) for x in issue.reprints],
            urls=[Url(primary=True, value=str(issue.resource_url))],
            credits=[
                Credit(
                    creator=Resource[str](id=str(x.id), value=x.creator),
                    roles=[
                        Resource[Role](id=str(r.id), value=load_role(value=r.name)) for r in x.role
                    ],
                )
                for x in issue.credits
            ],
            last_modified=datetime.now().astimezone(),
            locations=[],
            tags=[],
        )

    def _build_comic_info(self, series: Series, issue: Issue) -> ComicInfo:
        from comic_archive.metadata.comic_info import AgeRating  # noqa: PLC0415

        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

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

        return comic_info

    @rate_limit_retry()
    def fetch(self, search: Search) -> MetadataResult | None:
        if not search.series.metron and search.issue.metron:
            try:
                temp = self.session.issue(_id=search.issue.metron)
                if temp:
                    search.series.metron = temp.series.id
            except ApiError:
                pass

        series = self._fetch_series(search=search.series, filename=search.filename)
        if not series:
            return None

        issue = self._fetch_issue(
            series_id=series.id, search=search.issue, filename=search.filename
        )
        if not issue:
            return None

        return MetadataResult(
            comic_info=self._build_comic_info(series=series, issue=issue),
            metron_info=self._build_metron_info(series=series, issue=issue),
        )
