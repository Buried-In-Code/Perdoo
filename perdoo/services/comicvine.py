from __future__ import annotations

__all__ = ["Comicvine"]

import logging
import re

from rich.prompt import Confirm, Prompt
from simyan.comicvine import Comicvine as Simyan
from simyan.exceptions import ServiceError
from simyan.schemas.issue import Issue
from simyan.schemas.publisher import Publisher
from simyan.schemas.volume import Volume
from simyan.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, DatePrompt, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.models.metadata import Source
from perdoo.models.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Comicvine as ComicvineSettings

LOGGER = logging.getLogger(__name__)


def add_publisher_to_metadata(publisher: Publisher, metadata: Metadata) -> None:
    from perdoo.models.metadata import Resource

    resources = set(metadata.issue.series.publisher.resources)
    resources.add(Resource(source=Source.COMICVINE, value=publisher.id))
    metadata.issue.series.publisher.resources = list(resources)
    metadata.issue.series.publisher.title = publisher.name


def add_publisher_to_metron_info(publisher: Publisher, metron_info: MetronInfo) -> None:
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.publisher.id = publisher.id
    metron_info.publisher.value = publisher.name


def add_publisher_to_comic_info(publisher: Publisher, comic_info: ComicInfo) -> None:
    comic_info.publisher = publisher.name


def add_series_to_metadata(series: Volume, metadata: Metadata) -> None:
    from perdoo.models.metadata import Resource

    resources = set(metadata.issue.series.resources)
    resources.add(Resource(source=Source.COMICVINE, value=series.id))
    metadata.issue.series.resources = list(resources)
    metadata.issue.series.start_year = series.start_year
    metadata.issue.series.title = series.name


def add_series_to_metron_info(series: Volume, metron_info: MetronInfo) -> None:
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.series.id = series.id
    metron_info.series.name = series.name


def add_series_to_comic_info(series: Volume, comic_info: ComicInfo) -> None:
    comic_info.series = series.name


def add_issue_to_metadata(issue: Issue, metadata: Metadata) -> None:
    from perdoo.models.metadata import Credit, Resource, StoryArc, TitledResource

    resources = set(metadata.issue.resources)
    resources.add(Resource(source=Source.COMICVINE, value=issue.id))
    metadata.issue.resources = list(resources)
    metadata.issue.characters = [
        TitledResource(title=x.name, resources=[Resource(source=Source.COMICVINE, value=x.id)])
        for x in issue.characters
    ]
    metadata.issue.cover_date = issue.cover_date
    metadata.issue.credits = [
        Credit(
            creator=TitledResource(
                title=x.name, resources=[Resource(source=Source.COMICVINE, value=x.id)]
            ),
            roles=[TitledResource(title=r.strip()) for r in re.split(r"[~\r\n,]+", x.roles)],
        )
        for x in issue.creators
    ]
    metadata.issue.locations = [
        TitledResource(title=x.name, resources=[Resource(source=Source.COMICVINE, value=x.id)])
        for x in issue.locations
    ]
    metadata.issue.number = issue.number
    metadata.issue.store_date = issue.store_date
    metadata.issue.story_arcs = [
        StoryArc(title=x.name, resources=[Resource(source=Source.COMICVINE, value=x.id)])
        for x in issue.story_arcs
    ]
    metadata.issue.summary = issue.summary
    metadata.issue.teams = [
        TitledResource(title=x.name, resources=[Resource(source=Source.COMICVINE, value=x.id)])
        for x in issue.teams
    ]
    metadata.issue.title = issue.name


def add_issue_to_metron_info(issue: Issue, metron_info: MetronInfo) -> None:
    from perdoo.models.metron_info import Arc, Credit, Resource, Role, RoleResource, Source

    metron_info.arcs = [Arc(id=x.id, name=x.name) for x in issue.story_arcs]
    metron_info.characters = [Resource(id=x.id, value=x.name) for x in issue.characters]
    metron_info.cover_date = issue.cover_date or DatePrompt.ask("Cover Date")
    credits_ = []
    for x in issue.creators:
        roles = []
        for r in re.split(r"[~\r\n,]+", x.roles):
            try:
                roles.append(RoleResource(value=Role.load(value=r.strip())))
            except ValueError:  # noqa: PERF203
                roles.append(RoleResource(value=Role.OTHER))
        credits_.append(Credit(creator=Resource(id=x.id, value=x.name), roles=roles))
    metron_info.credits = credits_
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.id = Source(source=InformationSource.COMIC_VINE, value=issue.id)
    metron_info.locations = [Resource(id=x.id, value=x.name) for x in issue.locations]
    metron_info.number = issue.number
    metron_info.store_date = issue.store_date
    metron_info.summary = issue.summary
    metron_info.teams = [Resource(id=x.id, value=x.name) for x in issue.teams]
    metron_info.collection_title = issue.name


def add_issue_to_comic_info(issue: Issue, comic_info: ComicInfo) -> None:
    comic_info.character_list = [x.name for x in issue.characters]
    comic_info.credits = {
        x.name: [r.strip() for r in re.split(r"[~\r\n,]+", x.roles)] for x in issue.creators
    }
    comic_info.cover_date = issue.cover_date
    comic_info.location_list = [x.name for x in issue.locations]
    comic_info.number = issue.number
    comic_info.story_arc_list = [x.name for x in issue.story_arcs]
    comic_info.summary = issue.summary
    comic_info.team_list = [x.name for x in issue.teams]
    comic_info.title = issue.name


class Comicvine(BaseService):
    def __init__(self: Comicvine, settings: ComicvineSettings):
        cache = SQLiteCache(path=get_cache_dir() / "simyan.sqlite", expiry=14)
        self.session = Simyan(api_key=settings.api_key, cache=cache)

    def _search_publishers(self: Comicvine, title: str | None) -> int | None:
        title = title or Prompt.ask("Publisher title", console=CONSOLE)
        try:
            options = sorted(
                self.session.list_publishers({"filter": f"name:{title}"}), key=lambda x: x.name
            )
            if not options:
                LOGGER.warning("Unable to find any publishers with the title: '%s'", title)
            index = create_menu(
                options=[f"{x.id} | {x.name}" for x in options],
                title="Comicvine Publisher",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_publishers(title=None)
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_publisher(
        self: Comicvine,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> Publisher | None:
        publisher_id = None
        if metadata:
            publisher_id = next(
                (
                    x.value
                    for x in metadata.issue.series.publisher.resources
                    if x.source == Source.COMICVINE
                ),
                None,
            )
        if (
            not publisher_id
            and metron_info
            and metron_info.id
            and metron_info.id.source == InformationSource.COMIC_VINE
        ):
            publisher_id = metron_info.publisher.id
        if not publisher_id:
            publisher_id = self._search_publishers(
                title=metadata.issue.series.publisher.title
                if metadata
                else metron_info.publisher.value
                if metron_info
                else comic_info.publisher
            )
        if not publisher_id:
            return None
        try:
            publisher = self.session.get_publisher(publisher_id=publisher_id)
            if metadata:
                add_publisher_to_metadata(publisher=publisher, metadata=metadata)
            if metron_info:
                add_publisher_to_metron_info(publisher=publisher, metron_info=metron_info)
            if comic_info:
                add_publisher_to_comic_info(publisher=publisher, comic_info=comic_info)
            return publisher
        except ServiceError:
            LOGGER.exception("")
            return None

    def _search_series(self: Comicvine, publisher_id: int, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                [
                    x
                    for x in self.session.list_volumes({"filter": f"name:{title}"})
                    if x.publisher.id == publisher_id
                ],
                key=lambda x: (x.name, x.start_year),
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Series with a PublisherId: %s and the title: '%s'",
                    publisher_id,
                    title,
                )
            index = create_menu(
                options=[f"{x.id} | {x.name} ({x.start_year})" for x in options],
                title="Comicvine Series",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_series(publisher_id=publisher_id, title=None)
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_series(
        self: Comicvine,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
        publisher_id: int,
    ) -> Volume | None:
        series_id = None
        if metadata:
            series_id = next(
                (x.value for x in metadata.issue.series.resources if x.source == Source.COMICVINE),
                None,
            )
        if (
            not series_id
            and metron_info
            and metron_info.id
            and metron_info.id.source == InformationSource.COMIC_VINE
        ):
            series_id = metron_info.series.id
        if not series_id:
            series_id = self._search_series(
                publisher_id=publisher_id,
                title=metadata.issue.series.title
                if metadata
                else metron_info.series.name
                if metron_info
                else comic_info.series,
            )
        if not series_id:
            return False
        try:
            series = self.session.get_volume(volume_id=series_id)
            if metadata:
                add_series_to_metadata(series=series, metadata=metadata)
            if metron_info:
                add_series_to_metron_info(series=series, metron_info=metron_info)
            if comic_info:
                add_series_to_comic_info(series=series, comic_info=comic_info)
            return series
        except ServiceError:
            LOGGER.exception("")
            return None

    def _search_issues(self: Comicvine, series_id: int, number: str | None) -> int | None:
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
                return self._search_issues(series_id=series_id, number=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_issue(
        self: Comicvine,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
        series_id: int,
    ) -> Issue | None:
        issue_id = None
        if metadata:
            issue_id = next(
                (x.value for x in metadata.issue.resources if x.source == Source.COMICVINE), None
            )
        if (
            not issue_id
            and metron_info
            and metron_info.id
            and metron_info.id.source == InformationSource.COMIC_VINE
        ):
            issue_id = metron_info.id.value
        if not issue_id:
            issue_id = self._search_issues(
                series_id=series_id,
                number=metadata.issue.number
                if metadata
                else metron_info.number
                if metron_info
                else comic_info.number,
            )
        if not issue_id:
            return False
        try:
            issue = self.session.get_issue(issue_id=issue_id)
            if metadata:
                add_issue_to_metadata(issue=issue, metadata=metadata)
            if metron_info:
                add_issue_to_metron_info(issue=issue, metron_info=metron_info)
            if comic_info:
                add_issue_to_comic_info(issue=issue, comic_info=comic_info)
            return issue
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch(
        self: Comicvine,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> bool:
        if not metadata and not metron_info and not comic_info:
            return False

        publisher = self.fetch_publisher(
            metadata=metadata, metron_info=metron_info, comic_info=comic_info
        )
        if not publisher:
            return False
        series = self.fetch_series(
            metadata=metadata,
            metron_info=metron_info,
            comic_info=comic_info,
            publisher_id=publisher.id,
        )
        if not series:
            return False
        issue = self.fetch_issue(
            metadata=metadata, metron_info=metron_info, comic_info=comic_info, series_id=series.id
        )
        if not issue:
            return False
        return True
