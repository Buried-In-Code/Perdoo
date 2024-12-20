__all__ = ["Comicvine"]

import logging
import re
from datetime import datetime

from natsort import humansorted, ns
from requests.exceptions import JSONDecodeError
from rich.prompt import Confirm, Prompt
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_root
from perdoo.console import CONSOLE, create_menu
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.metadata.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Comicvine as ComicvineSettings
from perdoo.utils import IssueSearch, Search, SeriesSearch

LOGGER = logging.getLogger(__name__)


class Comicvine(BaseService[Volume, Issue]):
    def __init__(self, settings: ComicvineSettings):
        cache = SQLiteCache(path=get_cache_root() / "simyan.sqlite", expiry=14)
        self.session = Simyan(api_key=settings.api_key, cache=cache)

    def _search_series(self, name: str | None, volume: int | None, year: int | None) -> int | None:
        name = name or Prompt.ask("Volume Name", console=CONSOLE)
        try:
            options = sorted(
                self.session.list_volumes({"filter": f"name:{name}"}),
                key=lambda x: (
                    x.publisher.name if x.publisher and x.publisher.name else "",
                    x.name,
                    x.start_year or 0,
                ),
            )
            if year:
                options = [x for x in options if x.start_year == year]
            if not options:
                LOGGER.warning(
                    "Unable to find any Volumes with the Name and StartYear: '%s %s'", name, year
                )
            search = name
            if volume:
                search += f" v{volume}"
            if year:
                search += f" ({year})"
            index = create_menu(
                options=[
                    f"{x.id} | {x.publisher.name if x.publisher and x.publisher.name else ''}"
                    f" | {x.name} ({x.start_year})"
                    for x in options
                ],
                title="Comicvine Volume",
                subtitle=f"Searching for Volume '{search}'",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if year:
                LOGGER.info("Searching again without the StartYear")
                return self._search_series(name=name, volume=volume, year=None)
            if Confirm.ask("Search Again", console=CONSOLE):
                return self._search_series(name=None, volume=None, year=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def fetch_series(self, search: SeriesSearch) -> Volume | None:
        series_id = search.comicvine or self._search_series(
            name=search.name, volume=search.volume, year=search.year
        )
        if not series_id:
            return None
        try:
            series = self.session.get_volume(volume_id=series_id)
            search.comicvine = series_id
            return series
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def _search_issue(self, series_id: int, number: str | None) -> int | None:
        try:
            options = humansorted(
                self.session.list_issues(
                    {"filter": f"volume:{series_id},issue_number:{number}"}
                    if number
                    else {"filter": f"volume:{series_id}"}
                ),
                key=lambda x: (x.number, x.name),
                alg=ns.NA | ns.G,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Issues with the Volume and IssueNumber: '%s %s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.number} - {x.name or ''}" for x in options],
                title="Comicvine Issue",
                subtitle=f"Searching for Issue #{number}" if number else "",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if number:
                LOGGER.info("Searching again without the IssueNumber")
                return self._search_issue(series_id=series_id, number=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def fetch_issue(self, series_id: int, search: IssueSearch) -> Issue | None:
        issue_id = search.comicvine or self._search_issue(series_id=series_id, number=search.number)
        if not issue_id:
            return None
        try:
            issue = self.session.get_issue(issue_id=issue_id)
            search.comicvine = issue_id
            return issue
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def _process_metron_info(self, series: Volume, issue: Issue) -> MetronInfo | None:
        from perdoo.metadata.metron_info import (
            Arc,
            Credit,
            Id,
            Publisher,
            Resource,
            Role,
            Series,
            Url,
        )

        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        return MetronInfo(
            ids=[Id(primary=True, source=InformationSource.COMIC_VINE, value=str(issue.id))],
            publisher=Publisher(id=str(series.publisher.id), name=series.publisher.name),
            series=Series(id=str(series.id), name=series.name, start_year=series.start_year),
            collection_title=issue.name,
            number=issue.number,
            summary=issue.summary,
            cover_date=issue.cover_date,
            store_date=issue.store_date,
            arcs=[Arc(id=str(x.id), name=x.name) for x in issue.story_arcs],
            characters=[Resource[str](id=str(x.id), value=x.name) for x in issue.characters],
            teams=[Resource[str](id=str(x.id), value=x.name) for x in issue.teams],
            locations=[Resource[str](id=str(x.id), value=x.name) for x in issue.locations],
            urls=[Url(primary=True, value=issue.site_url)],
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
            ],
            last_modified=datetime.now(),
        )

    def _process_comic_info(self, series: Volume, issue: Issue) -> ComicInfo | None:
        comic_info = ComicInfo(
            title=issue.name,
            series=series.name,
            number=issue.number,
            summary=issue.summary,
            publisher=series.publisher.name if series.publisher else None,
            web=issue.site_url,
        )

        comic_info.cover_date = issue.cover_date
        comic_info.credits = {
            x.name: [r.strip() for r in re.split(r"[~\r\n,]+", x.roles) if r.strip()]
            for x in issue.creators
        }
        comic_info.character_list = [x.name for x in issue.characters]
        comic_info.team_list = [x.name for x in issue.teams]
        comic_info.location_list = [x.name for x in issue.locations]
        comic_info.story_arc_list = [x.name for x in issue.story_arcs]

        return comic_info

    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]:
        if not search.series.comicvine and search.issue.comicvine:
            try:
                temp = self.session.get_issue(issue_id=search.issue.comicvine)
                search.series.comicvine = temp.volume.id
            except (ServiceError, JSONDecodeError):
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
