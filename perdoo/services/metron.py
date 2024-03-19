from __future__ import annotations

__all__ = ["Metron"]

import logging

from mokkari.exceptions import ApiError
from mokkari.schemas.issue import Issue
from mokkari.schemas.publisher import Publisher
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.models.metadata import Source
from perdoo.models.metron_info import InformationSource
from perdoo.services import BaseService
from perdoo.settings import Metron as MetronSettings

LOGGER = logging.getLogger(__name__)


def add_publisher_to_metadata(publisher: Publisher, metadata: Metadata) -> None:
    from perdoo.models.metadata import Resource

    resources = set(metadata.issue.series.publisher.resources)
    if publisher.cv_id:
        resources.add(Resource(source=Source.COMICVINE, value=publisher.cv_id))
    resources.add(Resource(source=Source.METRON, value=publisher.id))
    metadata.issue.series.publisher.resources = list(resources)
    metadata.issue.series.publisher.title = publisher.name


def add_publisher_to_metron_info(publisher: Publisher, metron_info: MetronInfo) -> None:
    if not metron_info.id or metron_info.id.source == InformationSource.METRON:
        metron_info.publisher.id = publisher.id
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.publisher.id = publisher.cv_id
    metron_info.publisher.value = publisher.name


def add_publisher_to_comic_info(publisher: Publisher, comic_info: ComicInfo) -> None:
    comic_info.publisher = publisher.name


def add_series_to_metadata(series: Series, metadata: Metadata) -> None:
    from perdoo.models.metadata import Resource, TitledResource

    resources = set(metadata.issue.series.resources)
    if series.cv_id:
        resources.add(Resource(source=Source.COMICVINE, value=series.cv_id))
    resources.add(Resource(source=Source.METRON, value=series.id))
    metadata.issue.series.resources = list(resources)
    metadata.issue.series.genres = [
        TitledResource(resources=[Resource(source=Source.METRON, value=x.id)], title=x.name)
        for x in series.genres
    ]
    metadata.issue.series.start_year = series.year_began
    metadata.issue.series.title = series.name
    metadata.issue.series.volume = series.volume


def add_series_to_metron_info(series: Series, metron_info: MetronInfo) -> None:
    from perdoo.models.metron_info import Format

    if not metron_info.id or metron_info.id.source == InformationSource.METRON:
        metron_info.series.id = series.id
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.series.id = series.cv_id
    metron_info.series.name = series.name
    metron_info.series.sort_name = series.sort_name
    metron_info.series.volume = series.volume
    metron_info.series.format = Format.load(value=series.series_type.name)


def add_series_to_comic_info(series: Series, comic_info: ComicInfo) -> None:
    comic_info.series = series.name
    comic_info.volume = series.volume
    comic_info.genre_list = [x.name for x in series.genres]
    comic_info.format = series.series_type.name


def add_issue_to_metadata(issue: Issue, metadata: Metadata) -> None:
    from perdoo.models.metadata import Credit, Format, Resource, StoryArc, TitledResource

    resources = set(metadata.issue.resources)
    if issue.cv_id:
        resources.add(Resource(source=Source.COMICVINE, value=issue.cv_id))
    resources.add(Resource(source=Source.METRON, value=issue.id))
    metadata.issue.resources = list(resources)
    metadata.issue.story_arcs = [
        StoryArc(resources=[Resource(source=Source.METRON, value=x.id)], title=x.name)
        for x in issue.arcs
    ]
    metadata.issue.characters = [
        TitledResource(resources=[Resource(source=Source.METRON, value=x.id)], title=x.name)
        for x in issue.characters
    ]
    metadata.issue.title = issue.collection_title if issue.collection_title else None
    metadata.issue.cover_date = issue.cover_date
    metadata.issue.credits = [
        Credit(
            creator=TitledResource(
                resources=[Resource(source=Source.METRON, value=x.id)], title=x.creator
            ),
            roles=[
                TitledResource(resources=[Resource(source=Source.METRON, value=r.id)], title=r.name)
                for r in x.role
            ],
        )
        for x in issue.credits
    ]
    metadata.issue.summary = issue.desc
    metadata.issue.number = issue.number
    metadata.issue.page_count = issue.page_count or metadata.issue.page_count
    try:
        metadata.issue.format = Format.load(value=issue.series.series_type.name)
    except ValueError:
        metadata.issue.format = Format.COMIC
    metadata.issue.store_date = issue.store_date
    metadata.issue.teams = [
        TitledResource(resources=[Resource(source=Source.METRON, value=x.id)], title=x.name)
        for x in issue.teams
    ]


def add_issue_to_metron_info(issue: Issue, metron_info: MetronInfo) -> None:
    from perdoo.models.metron_info import (
        GTIN,
        AgeRating,
        Arc,
        Credit,
        Price,
        Resource,
        Role,
        RoleResource,
        Source,
    )

    if not metron_info.id or metron_info.id.source == InformationSource.METRON:
        metron_info.id = Source(source=InformationSource.METRON, value=issue.id)
    if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
        metron_info.id = Source(source=InformationSource.COMIC_VINE, value=issue.cv_id)
    metron_info.arcs = [Arc(id=x.id, name=x.name) for x in issue.arcs]
    metron_info.characters = [Resource(id=x.id, value=x.name) for x in issue.characters]
    metron_info.collection_title = issue.collection_title if issue.collection_title else None
    metron_info.cover_date = issue.cover_date
    credits_ = []
    for x in issue.credits:
        roles = []
        for r in x.role:
            try:
                roles.append(RoleResource(id=r.id, value=Role.load(value=r.name)))
            except ValueError:  # noqa: PERF203
                roles.append(RoleResource(id=r.id, value=Role.OTHER))
        credits_.append(Credit(creator=Resource(id=x.id, value=x.creator), roles=roles))
    metron_info.credits = credits_
    metron_info.summary = issue.desc
    metron_info.number = issue.number
    metron_info.page_count = issue.page_count or metron_info.page_count
    metron_info.prices = [Price(country="US", value=issue.price)] if issue.price else []
    metron_info.age_rating = AgeRating.load(value=issue.rating.name)
    metron_info.reprints = [Resource(id=x.id, value=x.issue) for x in issue.reprints]
    metron_info.url = str(issue.resource_url)
    metron_info.store_date = issue.store_date
    metron_info.stories = [Resource(value=x) for x in issue.story_titles]
    metron_info.teams = [Resource(id=x.id, value=x.name) for x in issue.teams]
    metron_info.gtin = GTIN(upc=issue.upc) if issue.upc else None


def add_issue_to_comic_info(issue: Issue, comic_info: ComicInfo) -> None:
    comic_info.story_arc_list = [x.name for x in issue.arcs]
    comic_info.character_list = [x.name for x in issue.characters]
    comic_info.title = issue.collection_title
    comic_info.cover_date = issue.cover_date
    comic_info.credits = {x.creator: [r.name for r in x.role] for x in issue.credits}
    comic_info.summary = issue.desc
    comic_info.number = issue.number
    comic_info.page_count = issue.page_count or comic_info.page_count
    comic_info.web = issue.resource_url
    comic_info.team_list = [x.name for x in issue.teams]


class Metron(BaseService[Publisher, Series, Issue]):
    def __init__(self: Metron, settings: MetronSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.session = Mokkari(username=settings.username, passwd=settings.password, cache=cache)

    def _get_publisher(self: Metron, comicvine_id: int) -> int | None:
        try:
            publisher = self.session.publishers_list({"cv_id": comicvine_id})
            if publisher and len(publisher) >= 1:
                return publisher[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_publishers(self: Metron, title: str | None) -> int | None:
        title = title or Prompt.ask("Publisher title", console=CONSOLE)
        try:
            options = sorted(
                self.session.publishers_list(params={"name": title}), key=lambda x: x.name
            )
            if not options:
                LOGGER.warning("Unable to find any publishers with the title: '%s'", title)
            index = create_menu(
                options=[f"{x.id} | {x.name}" for x in options],
                title="Metron Publisher",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_publishers(title=None)
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_publisher_id(self: Metron, metadata: Metadata, metron_info: MetronInfo) -> int | None:
        publisher_id = next(
            (
                x.value
                for x in metadata.issue.series.publisher.resources
                if x.source == Source.METRON
            ),
            None,
        ) or (
            metron_info.publisher.id
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not publisher_id:
            comicvine_id = next(
                (
                    x.value
                    for x in metadata.issue.series.publisher.resources
                    if x.source == Source.COMICVINE
                ),
                None,
            ) or (
                metron_info.publisher.id
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                publisher_id = self._get_publisher(comicvine_id=comicvine_id)
        return publisher_id or self._search_publishers(title=metadata.issue.series.publisher.title)

    def fetch_publisher(
        self: Metron, metadata: Metadata, metron_info: MetronInfo, comic_info: ComicInfo
    ) -> Publisher | None:
        publisher_id = self._get_publisher_id(metadata=metadata, metron_info=metron_info)
        if not publisher_id:
            return None
        try:
            publisher = self.session.publisher(_id=publisher_id)
            add_publisher_to_metadata(publisher=publisher, metadata=metadata)
            add_publisher_to_metron_info(publisher=publisher, metron_info=metron_info)
            add_publisher_to_comic_info(publisher=publisher, comic_info=comic_info)
            return publisher
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_series(self: Metron, comicvine_id: int) -> int | None:
        try:
            series = self.session.series_list({"cv_id": comicvine_id})
            if series and len(series) >= 1:
                return series[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_series(self: Metron, publisher_id: int, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                self.session.series_list(params={"publisher_id": publisher_id, "name": title}),
                key=lambda x: x.display_name,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Series with a PublisherId: %s and the title: '%s'",
                    publisher_id,
                    title,
                )
            index = create_menu(
                options=[f"{x.id} | {x.display_name}" for x in options],
                title="Metron Series",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_series(publisher_id=publisher_id, title=None)
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_series_id(
        self: Metron, publisher_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None:
        series_id = next(
            (x.value for x in metadata.issue.series.resources if x.source == Source.METRON), None
        ) or (
            metron_info.series.id
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not series_id:
            comicvine_id = next(
                (x.value for x in metadata.issue.series.resources if x.source == Source.COMICVINE),
                None,
            ) or (
                metron_info.series.id
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                series_id = self._get_series(comicvine_id=comicvine_id)
        return series_id or self._search_series(
            publisher_id=publisher_id, title=metadata.issue.series.title
        )

    def fetch_series(
        self: Metron,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        publisher_id: int,
    ) -> Series | None:
        series_id = self._get_series_id(
            publisher_id=publisher_id, metadata=metadata, metron_info=metron_info
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            add_series_to_metadata(series=series, metadata=metadata)
            add_series_to_metron_info(series=series, metron_info=metron_info)
            add_series_to_comic_info(series=series, comic_info=comic_info)
            return series
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue(self: Metron, comicvine_id: int) -> int | None:
        try:
            issue = self.session.issues_list({"cv_id": comicvine_id})
            if issue and len(issue) >= 1:
                return issue[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_issues(self: Metron, series_id: int, number: str | None) -> int | None:
        try:
            options = sorted(
                self.session.issues_list(params={"series_id": series_id, "number": number})
                if number
                else self.session.issues_list(params={"series_id": series_id}),
                key=lambda x: (x.number, x.issue_name),
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Issues with a SeriesId: %s and number: '%s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.issue_name}" for x in options],
                title="Metron Issue",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if number:
                LOGGER.info("Searching again without the issue number")
                return self._search_issues(series_id=series_id, number=None)
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue_id(
        self: Metron, series_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None:
        issue_id = next(
            (x.value for x in metadata.issue.resources if x.source == Source.METRON), None
        ) or (
            metron_info.id.value
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not issue_id:
            comicvine_id = next(
                (x.value for x in metadata.issue.resources if x.source == Source.COMICVINE), None
            ) or (
                metron_info.id.value
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                issue_id = self._get_issue(comicvine_id=comicvine_id)
        return issue_id or self._search_issues(series_id=series_id, number=metadata.issue.number)

    def fetch_issue(
        self: Metron,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        series_id: int,
    ) -> Issue | None:
        issue_id = self._get_issue_id(
            series_id=series_id, metadata=metadata, metron_info=metron_info
        )
        if not issue_id:
            return None
        try:
            issue = self.session.issue(_id=issue_id)
            add_issue_to_metadata(issue=issue, metadata=metadata)
            add_issue_to_metron_info(issue=issue, metron_info=metron_info)
            add_issue_to_comic_info(issue=issue, comic_info=comic_info)
            return issue
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch(
        self: Metron, metadata: Metadata, metron_info: MetronInfo, comic_info: ComicInfo
    ) -> bool:
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
