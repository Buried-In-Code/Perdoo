from __future__ import annotations

__all__ = ["Metron"]

import logging
from datetime import date

from mokkari.exceptions import ApiError
from mokkari.schemas.issue import Issue
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.models.metadata import Source
from perdoo.models.metron_info import InformationSource
from perdoo.services._base import BaseService
from perdoo.settings import Metron as MetronSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class Metron(BaseService[Series, Issue]):
    def __init__(self: Metron, settings: MetronSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.session = Mokkari(username=settings.username, passwd=settings.password, cache=cache)

    def _get_series_via_comicvine(self: Metron, comicvine_id: int | None) -> int | None:
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

    def _get_series_id(self: Metron, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                self.session.series_list(params={"name": title}), key=lambda x: x.display_name
            )
            if not options:
                LOGGER.warning("Unable to find any Series with the title: '%s'", title)
            index = create_menu(
                options=[
                    f"{x.id} | {x.display_name} v{x.volume}"
                    if x.volume > 1
                    else f"{x.id} | {x.display_name}"
                    for x in options
                ],
                title="Metron Series",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._get_series_id(title=None)
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch_series(self: Metron, details: Details) -> Series | None:
        series_id = (
            details.series.metron
            or self._get_series_via_comicvine(comicvine_id=details.series.comicvine)
            or self._get_series_id(title=details.series.search)
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            details.series.metron = series_id
            return series
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue_via_comicvine(self: Metron, comicvine_id: int | None) -> int | None:
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

    def _get_issue_id(self: Metron, series_id: int, number: str | None) -> int | None:
        try:
            options = sorted(
                self.session.issues_list(
                    params={"series_id": series_id, "number": number}
                    if number
                    else {"series_id": series_id}
                ),
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
                return self._get_issue_id(series_id=series_id, number=None)
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch_issue(self: Metron, series_id: int, details: Details) -> Issue | None:
        issue_id = (
            details.issue.metron
            or self._get_issue_via_comicvine(comicvine_id=details.issue.comicvine)
            or self._get_issue_id(series_id=series_id, number=details.issue.search)
        )
        if not issue_id:
            return None
        try:
            issue = self.session.issue(_id=issue_id)
            details.issue.metron = issue_id
            return issue
        except ApiError:
            LOGGER.exception("")
            return None

    def _process_metadata(
        self: Metron, metadata: Metadata | None, series: Series, issue: Issue
    ) -> Metadata | None:
        from perdoo.models.metadata import Credit, Format, Meta, Resource, StoryArc, TitledResource, Issue, Series

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
        resources.add(Resource(source=Source.METRON, value=series.publisher.id))
        metadata.issue.series.publisher.resources = list(resources)
        metadata.issue.series.publisher.title = series.publisher.name

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
                    TitledResource(
                        resources=[Resource(source=Source.METRON, value=r.id)], title=r.name
                    )
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

        return metadata

    def _process_metron_info(
        self: Metron, metron_info: MetronInfo | None, series: Series, issue: Issue
    ) -> MetronInfo | None:
        from perdoo.models.metron_info import (
            GTIN,
            AgeRating,
            Arc,
            Credit,
            Format,
            Price,
            Resource,
            Role,
            RoleResource,
            Source,
            Series,
        )

        metron_info = metron_info or MetronInfo(
            publisher=Resource(value=series.publisher.name),
            series=Series(name=series.name),
            cover_date=issue.cover_date,
        )

        if not metron_info.id or metron_info.id.source == InformationSource.METRON:
            metron_info.publisher.id = series.publisher.id
        metron_info.publisher.value = series.publisher.name

        if not metron_info.id or metron_info.id.source == InformationSource.METRON:
            metron_info.series.id = series.id
        if not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE:
            metron_info.series.id = series.cv_id
        metron_info.series.name = series.name
        metron_info.series.sort_name = series.sort_name
        metron_info.series.volume = series.volume
        metron_info.series.format = Format.load(value=series.series_type.name)

        if not metron_info.id or metron_info.id.source == InformationSource.METRON:
            metron_info.id = Source(source=InformationSource.METRON, value=issue.id)
        if issue.cv_id and (
            not metron_info.id or metron_info.id.source == InformationSource.COMIC_VINE
        ):
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

        return metron_info

    def _process_comic_info(
        self: Metron, comic_info: ComicInfo | None, series: Series, issue: Issue
    ) -> ComicInfo | None:
        comic_info = comic_info or ComicInfo()

        comic_info.publisher = series.publisher.name

        comic_info.series = series.name
        comic_info.volume = series.volume
        comic_info.genre_list = [x.name for x in series.genres]
        comic_info.format = series.series_type.name

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

        return comic_info

    def fetch(
        self: Metron,
        details: Details,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        if not details.series.metron and details.issue.metron:
            try:
                temp = self.session.issue(_id=details.issue.metron)
                details.series.metron = temp.series.id
            except ApiError:
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
