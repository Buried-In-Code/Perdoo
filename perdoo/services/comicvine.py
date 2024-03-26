from __future__ import annotations

__all__ = ["Comicvine"]

import logging
import re
from datetime import date

from rich.prompt import Confirm, Prompt
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, DatePrompt, create_menu
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

    def _process_metadata(
        self: Comicvine, metadata: Metadata | None, series: Volume, issue: Issue
    ) -> Metadata | None:
        from perdoo.models.metadata import (
            Credit,
            Issue,
            Meta,
            Resource,
            Series,
            StoryArc,
            TitledResource,
        )

        metadata = metadata or Metadata(
            issue=Issue(
                series=Series(
                    publisher=TitledResource(title=series.publisher.name), title=series.name
                ),
                number=issue.number,
            ),
            meta=Meta(date_=date.today()),
        )

        resources = set(metadata.issue.series.publisher.resources)
        resources.add(Resource(source=Source.COMICVINE, value=series.publisher.id))
        metadata.issue.series.publisher.resources = list(resources)
        metadata.issue.series.publisher.title = series.publisher.name

        resources = set(metadata.issue.series.resources)
        resources.add(Resource(source=Source.COMICVINE, value=series.id))
        metadata.issue.series.resources = list(resources)
        metadata.issue.series.start_year = series.start_year
        metadata.issue.series.title = series.name

        resources = set(metadata.issue.resources)
        resources.add(Resource(source=Source.COMICVINE, value=issue.id))
        metadata.issue.resources = list(resources)
        metadata.issue.characters = [
            TitledResource(resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name)
            for x in issue.characters
        ]
        metadata.issue.cover_date = issue.cover_date
        metadata.issue.credits = [
            Credit(
                creator=TitledResource(
                    resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name
                ),
                roles=[TitledResource(title=r.strip()) for r in re.split(r"[~\r\n,]+", x.roles)],
            )
            for x in issue.creators
        ]
        metadata.issue.locations = [
            TitledResource(resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name)
            for x in issue.locations
        ]
        metadata.issue.number = issue.number
        metadata.issue.store_date = issue.store_date
        metadata.issue.story_arcs = [
            StoryArc(resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name)
            for x in issue.story_arcs
        ]
        metadata.issue.summary = issue.summary
        metadata.issue.teams = [
            TitledResource(resources=[Resource(source=Source.COMICVINE, value=x.id)], title=x.name)
            for x in issue.teams
        ]
        metadata.issue.title = issue.name

        return metadata

    def _process_metron_info(
        self: BaseService, metron_info: MetronInfo | None, series: Volume, issue: Issue
    ) -> MetronInfo | None:
        from perdoo.models.metron_info import (
            Arc,
            Credit,
            Resource,
            Role,
            RoleResource,
            Series,
            Source,
        )

        metron_info = metron_info or MetronInfo(
            publisher=Resource(value=series.publisher.name),
            series=Series(name=series.name),
            cover_date=issue.cover_date or DatePrompt.ask("Cover date", console=CONSOLE),
            genres=[],
        )

        if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
            metron_info.publisher.id = series.publisher.id
        metron_info.publisher.value = series.publisher.name

        if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
            metron_info.series.id = series.id
        metron_info.series.name = series.name

        if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
            metron_info.id = Source(source=InformationSource.COMIC_VINE, value=issue.id)
        metron_info.collection_title = issue.name
        metron_info.number = issue.number
        metron_info.summary = issue.summary
        metron_info.cover_date = issue.cover_date or metron_info.cover_date
        metron_info.store_date = issue.store_date
        metron_info.arcs = [Arc(id=x.id, name=x.name) for x in issue.story_arcs]
        metron_info.characters = [Resource(id=x.id, value=x.name) for x in issue.characters]
        metron_info.teams = [Resource(id=x.id, value=x.name) for x in issue.teams]
        metron_info.locations = [Resource(id=x.id, value=x.name) for x in issue.locations]
        metron_info.url = issue.site_url
        credits = []  # noqa: A001
        for x in issue.creators:
            roles = []
            for r in re.split(r"[~\r\n,]+", x.roles):
                try:
                    roles.append(RoleResource(value=Role.load(value=r.strip())))
                except ValueError:  # noqa: PERF203
                    roles.append(RoleResource(value=Role.OTHER))
            credits.append(Credit(creator=Resource(id=x.id, value=x.name), roles=roles))
        metron_info.credits = credits

        return metron_info

    def _process_comic_info(
        self: BaseService, comic_info: ComicInfo | None, series: Volume, issue: Issue
    ) -> ComicInfo | None:
        comic_info = comic_info or ComicInfo()

        comic_info.title = issue.name
        comic_info.series = series.name
        comic_info.number = issue.number
        comic_info.summary = issue.summary
        comic_info.cover_date = issue.cover_date
        comic_info.credits = {
            x.name: [r.strip() for r in re.split(r"[~\r\n,]+", x.roles)] for x in issue.creators
        }
        comic_info.publisher = series.publisher.name if series.publisher else None
        comic_info.web = issue.site_url
        comic_info.character_list = [x.name for x in issue.characters]
        comic_info.team_list = [x.name for x in issue.teams]
        comic_info.location_list = [x.name for x in issue.locations]
        comic_info.story_arc_list = [x.name for x in issue.story_arcs]

        return comic_info

    def fetch(
        self: Comicvine,
        details: Details,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        if not details.series.comicvine and details.issue.comicvine:
            try:
                temp = self.session.get_issue(issue_id=details.issue.comicvine)
                details.series.comicvine = temp.volume.id
            except ServiceError:
                pass

        series = self.fetch_series(details=details)
        if not series:
            return metadata, metron_info, comic_info

        issue = self.fetch_issue(series_id=series.id, details=details)
        if not issue:
            return metadata, metron_info, comic_info

        metadata = self._process_metadata(metadata=metadata, series=series, issue=issue)
        metron_info = self._process_metron_info(metron_info=metron_info, series=series, issue=issue)
        comic_info = self._process_comic_info(comic_info=comic_info, series=series, issue=issue)

        return metadata, metron_info, comic_info
