__all__ = ["Metron"]

import logging
from datetime import datetime

from mokkari.exceptions import ApiError
from mokkari.schemas.issue import Issue
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from natsort import humansorted, ns
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_root
from perdoo.console import CONSOLE, create_menu
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Metron as MetronSettings
from perdoo.utils import IssueSearch, Search, SeriesSearch

LOGGER = logging.getLogger(__name__)


class Metron(BaseService[Series, Issue]):
    def __init__(self, settings: MetronSettings):
        cache = SqliteCache(db_name=str(get_cache_root() / "mokkari.sqlite"), expire=14)
        self.session = Mokkari(username=settings.username, passwd=settings.password, cache=cache)

    def _search_series_by_comicvine(self, comicvine_id: int | None) -> int | None:
        if not comicvine_id:
            return None
        try:
            series = self.session.series_list({"cv_id": comicvine_id})
            if series and len(series) >= 1:
                return series[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_series(self, name: str | None, volume: int | None, year: int | None) -> int | None:
        name = name or Prompt.ask("Series Name", console=CONSOLE)
        try:
            params = {"name": name}
            if volume:
                params["volume"] = volume
            if year:
                params["year_began"] = year
            options = sorted(
                self.session.series_list(params=params), key=lambda x: (x.display_name, x.volume)
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Series with the Name, Volume and YearBegan: '%s %s %s'",
                    name,
                    volume,
                    year,
                )
            search = name
            if volume:
                search += f" v{volume}"
            if year:
                search += f" ({year})"
            index = create_menu(
                options=[
                    f"{x.id} | {x.display_name} v{x.volume}"
                    if x.volume > 1
                    else f"{x.id} | {x.display_name}"
                    for x in options
                ],
                title="Metron Series",
                subtitle=f"Searching for Series '{search}'",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if year:
                LOGGER.info("Searching again without the YearBegan")
                return self._search_series(name=name, volume=volume, year=None)
            if volume:
                LOGGER.info("Searching again without the Volume")
                return self._search_series(name=name, volume=None, year=None)
            if Confirm.ask("Search Again", console=CONSOLE):
                return self._search_series(name=None, volume=None, year=None)
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch_series(self, search: SeriesSearch) -> Series | None:
        series_id = (
            search.metron
            or self._search_series_by_comicvine(comicvine_id=search.comicvine)
            or self._search_series(name=search.name, volume=search.volume, year=search.year)
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            search.metron = series_id
            return series
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_issue_by_comicvine(self, comicvine_id: int | None) -> int | None:
        if not comicvine_id:
            return None
        try:
            issues = self.session.issues_list({"cv_id": comicvine_id})
            if issues and len(issues) >= 1:
                return issues[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_issue(self, series_id: int, number: str | None) -> int | None:
        try:
            options = humansorted(
                self.session.issues_list(
                    params={"series_id": series_id, "number": number}
                    if number
                    else {"series_id": series_id}
                ),
                key=lambda x: (x.number, x.issue_name),
                alg=ns.NA | ns.G,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Issues with the SeriesId and Number: '%s %s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.issue_name}" for x in options],
                title="Metron Issue",
                subtitle=f"Searching for Issue #{number}" if number else "",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if number:
                LOGGER.info("Searching again without the Number")
                return self._search_issue(series_id=series_id, number=None)
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch_issue(self, series_id: int, search: IssueSearch) -> Issue | None:
        issue_id = (
            search.metron
            or self._search_issue_by_comicvine(comicvine_id=search.comicvine)
            or self._search_issue(series_id=series_id, number=search.number)
        )
        if not issue_id:
            return None
        try:
            issue = self.session.issue(_id=issue_id)
            search.metron = issue_id
            return issue
        except ApiError:
            LOGGER.exception("")
            return None

    def _process_metron_info(self, series: Series, issue: Issue) -> MetronInfo | None:
        from perdoo.metadata.metron_info import (
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
            urls=[Url(primary=True, value=issue.resource_url)],
            credits=[
                Credit(
                    creator=Resource[str](id=str(x.id), value=x.creator),
                    roles=[
                        Resource[Role](id=str(r.id), value=load_role(value=r.name)) for r in x.role
                    ],
                )
                for x in issue.credits
            ],
            last_modified=datetime.now(),
        )

    def _process_comic_info(self, series: Series, issue: Issue) -> ComicInfo | None:
        from perdoo.metadata.comic_info import AgeRating

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
            web=issue.resource_url,
            page_count=issue.page_count or 0,
            format=series.series_type.name,
            age_rating=load_age_rating(value=issue.rating.name),
        )

        comic_info.cover_date = issue.cover_date
        comic_info.credits = {x.creator: [r.name for r in x.role] for x in issue.credits}
        comic_info.genre_list = [x.name for x in series.genres]
        comic_info.character_list = [x.name for x in issue.characters]
        comic_info.team_list = [x.name for x in issue.teams]
        comic_info.story_arc_list = [x.name for x in issue.arcs]

        return comic_info

    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]:
        if not search.series.metron and search.issue.metron:
            try:
                temp = self.session.issue(_id=search.issue.metron)
                search.series.metron = temp.series.id
            except ApiError:
                pass

        series = self.fetch_series(search=search.series)
        if not series:
            return None, None

        issue = self.fetch_issue(series_id=series.id, search=search.issue)
        if not issue:
            return None, None

        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)

        return metron_info, comic_info
