from __future__ import annotations

__all__ = ["Marvel"]

import logging

from esak.comic import Comic
from esak.exceptions import ApiError
from esak.series import Series
from esak.session import Session as Esak
from esak.sqlite_cache import SqliteCache
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
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
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
                options=[f"{x.id} | {x.title} ({x.start_year})" for x in options],
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
        from perdoo.models.metadata import Meta, Issue, TitledResource, Resource, Source
        
        return Metadata(
            issue=Issue(
                characters = [
                    TitledResource(title=x.name, resources=[Resource(source=Source.MARVEL, value=x.id)]) for x in issue.characters
                ],
                credits = [
                    Credit(
                        creator = TitledResource(title=x.name, resources=[Resource(source=Source.MARVEL, value=x.id)]),
                        roles = [
                            TitledResource(title=x.role.strip())
                        ]
                    ) for x in issue.creators
                ],
            ),
            meta=Meta(date_=date.today()),
        )

    def _process_metron_info(self: Marvel, series: Series, issue: Comic) -> MetronInfo | None:
        pass

    def _process_comic_info(self: Marvel, series: Series, issue: Comic) -> ComicInfo | None:
        # Series
        id: int
        title: str
        description: str
        resource_uri: url
        start_year: int
        end_year: int = 2099
        rating: str
        modified: datetime
        thumbnail: url
        comics: list[Summary]
        stories: list[Summary]
        events: list[Summary]
        characters: list[Summary]
        creators: list[Summary]
        next: list[Summary]
        previous: list[Summary]
        
        # Comic
        id: int
        digital_id: int = 0
        title: str
        issue_number: int = 0
        variant_description: str
        description: str | None = None
        modified: datetime
        isbn: str
        upc: str
        diamond_code: str
        ean: str
        issn: str
        format: str
        page_count: int
        text_objects: list[TextObject]
        resource_uri: url
        urls: list[Urls]
        series: list[Series]
        variants: list[Summary]
        collections: list[Summary]
        collected_issues: list[Summary]
        dates: list[Dates]
        prices: list[Price]
        thumbnail: url
        images: list[url]
        creators: list[Summary]
        characters: list[Summary]
        stories: list[Summary]
        events: list[Summary]
        
        # Summary
        id: int
        name: str
        resource_uri: url
        type: str
        role: str
        
        # Dates
        on_sale: date
        foc: date
        unlimited: date

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
