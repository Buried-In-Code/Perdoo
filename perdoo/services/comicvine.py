__all__ = ["Comicvine"]

import logging
import re
from datetime import datetime

from natsort import humansorted, ns
from prompt_toolkit.styles import Style
from questionary import Choice, confirm, select, text
from requests.exceptions import JSONDecodeError
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_root
from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Comicvine as ComicvineSettings
from perdoo.utils import IssueSearch, Search, SeriesSearch

LOGGER = logging.getLogger(__name__)
DEFAULT_CHOICE = Choice(title="None of the Above", value=None)


class Comicvine(BaseService[Volume, Issue]):
    def __init__(self, settings: ComicvineSettings):
        cache = SQLiteCache(path=get_cache_root() / "simyan.sqlite", expiry=14)
        self.session = Simyan(api_key=settings.api_key, cache=cache)

    def _search_series(
        self, name: str | None, volume: int | None, year: int | None, filename: str
    ) -> int | None:
        name = name or text(message="Volume Name").ask()
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
            if options:
                search = name
                if volume:
                    search += f" v{volume}"
                if year:
                    search += f" ({year})"
                choices = [
                    Choice(
                        title=[
                            (
                                "class:dim",
                                f"{x.id} | {x.publisher.name if x.publisher and x.publisher.name else ''} | ",  # noqa: E501
                            ),
                            ("class:title", f"{x.name} ({x.start_year})"),
                        ],
                        description=f"https://comicvine.gamespot.com/volumes/4050-{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                choices.append(DEFAULT_CHOICE)
                selected = select(
                    f"Searching Comicvine for Volumes matching '{filename}'"
                    if not year
                    else f"Searching Comicvine for Volume '{search}'",
                    default=DEFAULT_CHOICE,
                    choices=choices,
                    style=Style([("dim", "dim")]),
                ).ask()
                if selected and selected != DEFAULT_CHOICE.title:
                    return selected.id
            else:
                LOGGER.warning(
                    "Unable to find any Volumes on Comicvine for the file: '%s'", filename
                )
            if year:
                LOGGER.info("Searching again without the StartYear")
                return self._search_series(name=name, volume=volume, year=None, filename=filename)
            if confirm(message="Search Again", default=False).ask():
                return self._search_series(name=None, volume=None, year=None, filename=filename)
        except ServiceError as err:
            LOGGER.error(err)
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")
        return None

    def fetch_series(self, search: SeriesSearch, filename: str) -> Volume | None:
        series_id = search.comicvine or self._search_series(
            name=search.name, volume=search.volume, year=search.year, filename=filename
        )
        if not series_id:
            return None
        try:
            series = self.session.get_volume(volume_id=series_id)
            search.comicvine = series_id
            return series
        except ServiceError as err:
            LOGGER.error(err)
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")
            return None
        if search.comicvine:
            search.comicvine = None
            return self.fetch_series(search=search, filename=filename)
        return None

    def _search_issue(self, series_id: int, number: str | None, filename: str) -> int | None:
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
            if options:
                choices = [
                    Choice(
                        title=[
                            ("class:dim", f"{x.id} | "),
                            ("class:title", f"{x.number} - {x.name or ''}"),
                        ],
                        description=f"https://comicvine.gamespot.com/issues/4000-{x.id}",
                        value=x,
                    )
                    for x in options
                ]
                choices.append(DEFAULT_CHOICE)
                selected = select(
                    f"Searching Comicvine for Issues matching '{filename}'"
                    if not number
                    else f"Searching Comicvine for Issues with number '{number}'",
                    default=DEFAULT_CHOICE,
                    choices=choices,
                    style=Style([("dim", "dim")]),
                ).ask()
                if selected and selected != DEFAULT_CHOICE.title:
                    return selected.id
            else:
                LOGGER.warning(
                    "Unable to find any Issues on Comicvine for the file: '%s'", filename
                )
            if number:
                LOGGER.info("Searching again without the IssueNumber")
                return self._search_issue(series_id=series_id, number=None, filename=filename)
        except ServiceError as err:
            LOGGER.error(err)
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")
        return None

    def fetch_issue(self, series_id: int, search: IssueSearch, filename: str) -> Issue | None:
        issue_id = search.comicvine or self._search_issue(
            series_id=series_id, number=search.number, filename=filename
        )
        if not issue_id:
            return None
        try:
            issue = self.session.get_issue(issue_id=issue_id)
            search.comicvine = issue_id
            return issue
        except ServiceError as err:
            LOGGER.error(err)
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")
            return None
        if search.comicvine:
            search.comicvine = None
            return self.fetch_issue(series_id=series_id, search=search, filename=filename)
        return None

    def _process_metron_info(self, series: Volume, issue: Issue) -> MetronInfo | None:
        from perdoo.comic.metadata.metron_info import (  # noqa: PLC0415
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

        series = self.fetch_series(search=search.series, filename=search.filename)
        if not series:
            return None, None

        issue = self.fetch_issue(series_id=series.id, search=search.issue, filename=search.filename)
        if not issue:
            return None, None

        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)

        return metron_info, comic_info
