from __future__ import annotations

__all__ = ["Marvel"]

import logging
from datetime import date

from esak.comic import Comic
from esak.exceptions import ApiError
from esak.series import Series
from esak.session import Session as Esak
from esak.sqlite_cache import SqliteCache
from pydantic import HttpUrl
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.services._base import BaseService
from perdoo.settings import Marvel as MarvelSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class Marvel(BaseService[Series, Comic]):
    def __init__(self: Marvel, settings: MarvelSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "esak.sqlite"), expire=14)
        self.session = Esak(
            public_key=settings.public_key, private_key=settings.private_key, cache=cache
        )

    def _get_series_id(self: Marvel, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                self.session.series_list(params={"title": title}),
                key=lambda x: (x.title, x.start_year),
            )
            if not options:
                LOGGER.warning("Unable to find any Series with the title: '%s'", title)
            index = create_menu(
                options=[f"{x.id} | {x.title}" for x in options],
                title="Marvel Series",
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

    def fetch_series(self: Marvel, details: Details) -> Series | None:
        series_id = details.series.marvel or self._get_series_id(title=details.series.search)
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            details.series.marvel = series_id
            return series
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue_id(self: Marvel, series_id: int, number: str | None) -> int | None:
        try:
            options = sorted(
                self.session.comics_list(
                    params={"noVariants": True, "series": series_id, "issueNumber": number}
                    if number
                    else {"noVariants": True, "series": series_id}
                ),
                key=lambda x: x.issue_number,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Comics with a SeriesId: %s and number: '%s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[
                    f"{x.id} | {x.series.name} #{x.issue_number} - {x.format}" for x in options
                ],
                title="Marvel Comic",
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

    def fetch_issue(self: Marvel, series_id: int, details: Details) -> Comic | None:
        issue_id = details.issue.marvel or self._get_issue_id(
            series_id=series_id, number=details.issue.search
        )
        if not issue_id:
            return None
        try:
            issue = self.session.comic(_id=issue_id)
            details.issue.marvel = issue_id
            return issue
        except ApiError:
            LOGGER.exception("")
            return None

    def _process_metadata(self: Marvel, series: Series, issue: Comic) -> Metadata | None:
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
            Source,
            StoryArc,
            TitledResource,
        )

        return Metadata(
            issue=Issue(
                characters=[
                    TitledResource(
                        title=x.name, resources=[Resource(source=Source.MARVEL, value=x.id)]
                    )
                    for x in issue.characters
                ],
                credits=[
                    Credit(
                        creator=TitledResource(
                            title=x.name, resources=[Resource(source=Source.MARVEL, value=x.id)]
                        ),
                        roles=[TitledResource(title=x.role.strip())],
                    )
                    for x in issue.creators
                ],
                format=load_format(value=issue.format),
                number=issue.issue_number,
                page_count=issue.page_count,
                resources=[Resource(source=Source.MARVEL, value=issue.id)],
                series=Series(
                    publisher=TitledResource(title="Marvel"),
                    resources=[Resource(source=Source.MARVEL, value=series.id)],
                    start_year=series.start_year,
                ),
                store_date=issue.dates.on_sale,
                story_arcs=[
                    StoryArc(title=x.name, resources=[Resource(source=Source.MARVEL, value=x.id)])
                    for x in issue.events
                ],
                summary=issue.description,
                title=issue.title,
            ),
            meta=Meta(date_=date.today()),
        )

    def _process_metron_info(self: Marvel, series: Series, issue: Comic) -> MetronInfo | None:
        def load_format(value: str) -> Format:
            try:
                return Format.load(value=value.strip())
            except ValueError:
                return Format.SERIES

        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

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
            InformationList,
            InformationSource,
            Price,
            Resource,
            Role,
            RoleResource,
            Series,
            Source,
        )

        return MetronInfo(
            id=InformationList[Source](
                primary=Source(source=InformationSource.MARVEL, value=issue.id)
            ),
            publisher=Resource(value="Marvel"),
            series=Series(id=series.id, name=series.title, format=load_format(value=issue.format)),
            collection_title=issue.title,
            number=issue.issue_number,
            stories=[Resource(id=x.id, value=x.name) for x in issue.stories],
            summary=issue.description,
            prices=[Price(country="US", value=issue.prices.print)] if issue.prices else [],
            store_date=issue.dates.on_sale,
            page_count=issue.page_count,
            arcs=[Arc(id=x.id, name=x.name) for x in issue.events],
            characters=[Resource(id=x.id, value=x.name) for x in issue.characters],
            gtin=GTIN(isbn=issue.isbn, upc=issue.upc) if issue.isbn and issue.upc else None,
            age_rating=load_age_rating(value=series.rating),
            url=InformationList[HttpUrl](primary=issue.urls.detail),
            credits=[
                Credit(
                    creator=Resource(id=x.id, value=x.name),
                    roles=[RoleResource(value=load_role(value=x.role))],
                )
                for x in issue.creators
            ],
        )

    def _process_comic_info(self: Marvel, series: Series, issue: Comic) -> ComicInfo | None:
        def load_age_rating(value: str) -> AgeRating:
            try:
                return AgeRating.load(value=value.strip())
            except ValueError:
                return AgeRating.UNKNOWN

        from perdoo.models.comic_info import AgeRating

        comic_info = ComicInfo(
            title=issue.title,
            series=series.title,
            number=issue.issue_number,
            summary=issue.description,
            publisher="Marvel",
            web=issue.urls.detail,
            page_count=issue.page_count,
            format=issue.format,
            age_rating=load_age_rating(value=series.rating),
        )

        comic_info.credits = {x.name: x.role.strip() for x in issue.creators}
        comic_info.character_list = [x.name for x in issue.characters]
        comic_info.story_arc_list = [x.name for x in issue.events]

        return comic_info

    def fetch(
        self: Marvel, details: Details
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        if not details.series.marvel and details.issue.marvel:
            try:
                temp = self.session.comic(_id=details.issue.marvel)
                details.series.marvel = temp.series.id
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
