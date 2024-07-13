from __future__ import annotations

__all__ = ["Metron"]

import logging
from datetime import date

from mokkari.exceptions import ApiError
from mokkari.schemas.issue import Issue
from mokkari.schemas.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from pydantic import HttpUrl
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
                self.session.series_list(params={"name": title}),
                key=lambda x: (x.display_name, x.volume),
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

    def _process_metadata(self: Metron, series: Series, issue: Issue) -> Metadata | None:
        def load_format(value: str) -> Format:
            try:
                return Format.load(value=value.strip())
            except ValueError:
                return Format.COMIC

        from perdoo.models.metadata import (
            Credit,
            Format,
            Issue,
            Meta,
            Resource,
            Series,
            StoryArc,
            TitledResource,
        )

        resources = [Resource(source=Source.METRON, value=issue.id)]
        if issue.cv_id:
            resources.append(Resource(source=Source.COMICVINE, value=issue.cv_id))

        series_resources = [Resource(source=Source.METRON, value=series.id)]
        if series.cv_id:
            resources.append(Resource(source=Source.COMICVINE, value=series.cv_id))

        return Metadata(
            issue=Issue(
                characters=[
                    TitledResource(
                        resources=[Resource(source=Source.METRON, value=x.id)], title=x.name
                    )
                    for x in issue.characters
                ],
                cover_date=issue.cover_date,
                credits=[
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
                ],
                format=load_format(value=issue.series.series_type.name),
                number=issue.number,
                page_count=issue.page_count or 0,
                resources=resources,
                series=Series(
                    genres=[
                        TitledResource(
                            resources=[Resource(source=Source.METRON, value=x.id)], title=x.name
                        )
                        for x in series.genres
                    ],
                    publisher=TitledResource(
                        resources=[Resource(source=Source.METRON, value=series.publisher.id)],
                        title=series.publisher.name,
                    ),
                    resources=series_resources,
                    start_year=series.year_began,
                    title=series.name,
                    volume=series.volume,
                ),
                store_date=issue.store_date,
                story_arcs=[
                    StoryArc(resources=[Resource(source=Source.METRON, value=x.id)], title=x.name)
                    for x in issue.arcs
                ],
                summary=issue.desc,
                teams=[
                    TitledResource(
                        resources=[Resource(source=Source.METRON, value=x.id)], title=x.name
                    )
                    for x in issue.teams
                ],
                title=issue.collection_title or None,
            ),
            meta=Meta(date_=date.today()),
        )

    def _process_metron_info(self: Metron, series: Series, issue: Issue) -> MetronInfo | None:
        def load_role(value: str) -> Role:
            try:
                return Role.load(value=value.strip())
            except ValueError:
                return Role.OTHER

        from perdoo.models.metron_info import (
            GTIN,
            AgeRating,
            Arc,
            Credit,
            Format,
            Genre,
            GenreResource,
            InformationList,
            Price,
            Resource,
            Role,
            RoleResource,
            Series,
            Source,
            Universe,
        )

        return MetronInfo(
            id=InformationList[Source](
                primary=Source(source=InformationSource.METRON, value=issue.id),
                alternative=[Source(source=InformationSource.COMIC_VINE, value=issue.cv_id)]
                if issue.cv_id
                else [],
            ),
            publisher=Resource(id=series.publisher.id, value=series.publisher.name),
            series=Series(
                id=series.id,
                name=series.name,
                sort_name=series.sort_name,
                volume=series.volume,
                format=Format.load(value=series.series_type.name),
            ),
            collection_title=issue.collection_title or None,
            number=issue.number,
            stories=[Resource(value=x) for x in issue.story_titles],
            summary=issue.desc,
            prices=[Price(country="US", value=issue.price)] if issue.price else [],
            cover_date=issue.cover_date,
            store_date=issue.store_date,
            page_count=issue.page_count or 0,
            genres=[
                GenreResource(id=x.id, value=Genre.load(value=x.name)) for x in issue.series.genres
            ],
            arcs=[Arc(id=x.id, name=x.name) for x in issue.arcs],
            characters=[Resource(id=x.id, value=x.name) for x in issue.characters],
            teams=[Resource(id=x.id, value=x.name) for x in issue.teams],
            universes=[Universe(id=x.id, name=x.name) for x in issue.universes],
            gtin=GTIN(isbn=issue.isbn or None, upc=issue.upc or None)
            if issue.isbn or issue.upc
            else None,
            age_rating=AgeRating.load(value=issue.rating.name),
            reprints=[Resource(id=x.id, value=x.issue) for x in issue.reprints],
            url=InformationList[HttpUrl](primary=issue.resource_url),
            credits=[
                Credit(
                    creator=Resource(id=x.id, value=x.creator),
                    roles=[RoleResource(id=r.id, value=load_role(value=r.name)) for r in x.role],
                )
                for x in issue.credits
            ],
        )

    def _process_comic_info(self: Metron, series: Series, issue: Issue) -> ComicInfo | None:
        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

        from perdoo.models.comic_info import AgeRating

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

    def fetch(
        self: Metron, details: Details
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        if not details.series.metron and details.issue.metron:
            try:
                temp = self.session.issue(_id=details.issue.metron)
                details.series.metron = temp.series.id
            except ApiError:
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
