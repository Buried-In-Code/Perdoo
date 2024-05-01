from __future__ import annotations

__all__ = ["Comicvine"]

import logging
import re
from datetime import date

from pydantic import HttpUrl
from rich.prompt import Confirm, Prompt
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.models.metadata import Source
from perdoo.models.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Comicvine as ComicvineSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class Comicvine(BaseService[Volume, Issue]):
    def __init__(self: Comicvine, settings: ComicvineSettings):
        cache = SQLiteCache(path=get_cache_dir() / "simyan.sqlite", expiry=14)
        self.session = Simyan(api_key=settings.api_key, cache=cache)

    def _get_series_id(self: Comicvine, title: str | None) -> int | None:
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
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._get_series_id(title=None)
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_series(self: Comicvine, details: Details) -> Volume | None:
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

    def _get_issue_id(self: Comicvine, series_id: int, number: str | None) -> int | None:
        try:
            options = sorted(
                self.session.list_issues(
                    {"filter": f"volume:{series_id},issue_number:{number}"}
                    if number
                    else {"filter": f"volume:{series_id}"}
                ),
                key=lambda x: (x.number, x.name),
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

    def fetch_issue(self: Comicvine, series_id: int, details: Details) -> Issue | None:
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

    def _process_metadata(self: Comicvine, series: Volume, issue: Issue) -> Metadata | None:
        from perdoo.models.metadata import (
            Credit,
            Issue,
            Meta,
            Resource,
            Series,
            StoryArc,
            TitledResource,
        )

        return Metadata(
            issue=Issue(
                characters=[
                    TitledResource(
                        resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                    )
                    for x in issue.characters
                ],
                cover_date=issue.cover_date,
                credits=[
                    Credit(
                        creator=TitledResource(
                            resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                        ),
                        roles=[
                            TitledResource(title=r.strip())
                            for r in re.split(r"[~\r\n,]+", x.roles)
                            if r.strip()
                        ],
                    )
                    for x in issue.creators
                ],
                locations=[
                    TitledResource(
                        resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                    )
                    for x in issue.locations
                ],
                number=issue.number,
                resources=[Resource(source=Source.COMICVINE, value=issue.id)],
                series=Series(
                    publisher=TitledResource(
                        resources=[Resource(source=Source.COMICVINE, value=series.publisher.id)],
                        title=series.publisher.name,
                    ),
                    resources=[Resource(source=Source.COMICVINE, value=series.id)],
                    start_year=series.start_year,
                    title=series.name,
                ),
                store_date=issue.store_date,
                story_arcs=[
                    StoryArc(
                        resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                    )
                    for x in issue.story_arcs
                ],
                summary=issue.summary,
                teams=[
                    TitledResource(
                        resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                    )
                    for x in issue.teams
                ],
                title=issue.name,
            ),
            meta=Meta(date_=date.today()),
        )

    def _process_metron_info(self: BaseService, series: Volume, issue: Issue) -> MetronInfo | None:
        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        from perdoo.models.metron_info import (
            Arc,
            Credit,
            InformationList,
            Resource,
            Role,
            RoleResource,
            Series,
            Source,
        )

        return MetronInfo(
            id=InformationList[Source](
                primary=Source(source=InformationSource.COMIC_VINE, value=issue.id)
            ),
            publisher=Resource(id=series.publisher.id, value=series.publisher.name),
            series=Series(id=series.id, name=series.name),
            collection_title=issue.name,
            number=issue.number,
            summary=issue.summary,
            cover_date=issue.cover_date,
            store_date=issue.store_date,
            arcs=[Arc(id=x.id, name=x.name) for x in issue.story_arcs],
            characters=[Resource(id=x.id, value=x.name) for x in issue.characters],
            teams=[Resource(id=x.id, value=x.name) for x in issue.teams],
            locations=[Resource(id=x.id, value=x.name) for x in issue.locations],
            url=InformationList[HttpUrl](primary=issue.site_url),
            credits=[
                Credit(
                    creator=Resource(id=x.id, value=x.name),
                    roles=[
                        RoleResource(value=load_role(value=r.strip()))
                        for r in re.split(r"[~\r\n,]+", x.roles)
                        if r.strip()
                    ],
                )
                for x in issue.creators
            ],
        )

    def _process_comic_info(self: BaseService, series: Volume, issue: Issue) -> ComicInfo | None:
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

    def fetch(
        self: Comicvine, details: Details
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        if not details.series.comicvine and details.issue.comicvine:
            try:
                temp = self.session.get_issue(issue_id=details.issue.comicvine)
                details.series.comicvine = temp.volume.id
            except ServiceError:
                pass

        series = self.fetch_series(details=details)
        if not series:
            return None, None, None

        issue = self.fetch_issue(series_id=series.id, details=details)
        if not issue:
            return None, None, None

        metadata = self._process_metadata(series=series, issue=issue)
        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)

        return metadata, metron_info, comic_info
