__all__ = ["Comicvine"]

import logging
import re
from datetime import datetime

from natsort import humansorted, ns
from pydantic import HttpUrl
from requests.exceptions import JSONDecodeError
from rich.prompt import Confirm, Prompt
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_root
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, MetronInfo
from perdoo.models.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Comicvine as ComicvineSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class Comicvine(BaseService[Volume, Issue]):
    def __init__(self, settings: ComicvineSettings):
        cache = SQLiteCache(path=get_cache_root() / "simyan.sqlite", expiry=14)
        self.session = Simyan(api_key=settings.api_key, cache=cache)

    def _get_series_id(self, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                self.session.list_volumes({"filter": f"name:{title}"}),
                key=lambda x: (
                    x.publisher.name if x.publisher and x.publisher.name else "",
                    x.name,
                    x.start_year or 0,
                ),
            )
            if not options:
                LOGGER.warning("Unable to find any Series with the title: '%s'", title)
            index = create_menu(
                options=[
                    f"{x.id} | {x.publisher.name if x.publisher and x.publisher.name else ''}"
                    f" | {x.name} ({x.start_year})"
                    for x in options
                ],
                title="Comicvine Series",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Search Again", console=CONSOLE):
                return None
            return self._get_series_id(title=None)
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def fetch_series(self, details: Details) -> Volume | None:
        series_id = details.series.comicvine or self._get_series_id(title=details.series.search)
        if not series_id:
            return None
        try:
            series = self.session.get_volume(volume_id=series_id)
            details.series.comicvine = series_id
            return series
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def _get_issue_id(self, series_id: int, number: str | None) -> int | None:
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
                    "Unable to find any Issues with a SeriesId: %s and the issue number: '%s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.number} - {x.name or ''}" for x in options],
                title="Comicvine Issue",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if number:
                LOGGER.info("Searching again without the issue number")
                return self._get_issue_id(series_id=series_id, number=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def fetch_issue(self, series_id: int, details: Details) -> Issue | None:
        issue_id = details.issue.comicvine or self._get_issue_id(
            series_id=series_id, number=details.issue.search
        )
        if not issue_id:
            return None
        try:
            issue = self.session.get_issue(issue_id=issue_id)
            details.issue.comicvine = issue_id
            return issue
        except ServiceError:
            LOGGER.exception("")
            return None
        except JSONDecodeError:
            LOGGER.error("Unable to get response from Comicvine")  # noqa: TRY400
            return None

    def _process_metron_info(self, series: Volume, issue: Issue) -> MetronInfo | None:
        from perdoo.models.metron_info import (
            Arc,
            Credit,
            InformationList,
            Publisher,
            Resource,
            Role,
            Series,
            Source,
        )

        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        return MetronInfo(
            id=InformationList[Source](
                primary=Source(source=InformationSource.COMIC_VINE, value=issue.id)
            ),
            publisher=Publisher(id=series.publisher.id, name=series.publisher.name),
            series=Series(id=series.id, name=series.name, start_year=series.start_year),
            collection_title=issue.name,
            number=issue.number,
            summary=issue.summary,
            cover_date=issue.cover_date,
            store_date=issue.store_date,
            arcs=[Arc(id=x.id, name=x.name) for x in issue.story_arcs],
            characters=[Resource[str](id=x.id, value=x.name) for x in issue.characters],
            teams=[Resource[str](id=x.id, value=x.name) for x in issue.teams],
            locations=[Resource[str](id=x.id, value=x.name) for x in issue.locations],
            urls=InformationList[HttpUrl](primary=issue.site_url),
            credits=[
                Credit(
                    creator=Resource[str](id=x.id, value=x.name),
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

    def fetch(self, details: Details) -> tuple[MetronInfo | None, ComicInfo | None]:
        if not details.series.comicvine and details.issue.comicvine:
            try:
                temp = self.session.get_issue(issue_id=details.issue.comicvine)
                details.series.comicvine = temp.volume.id
            except (ServiceError, JSONDecodeError):
                pass

        series = self.fetch_series(details=details)
        if not series:
            return None, None

        issue = self.fetch_issue(series_id=series.id, details=details)
        if not issue:
            return None, None

        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)

        return metron_info, comic_info
