__all__ = ["GrandComicsDatabase"]

import logging
import re
from datetime import datetime
from decimal import Decimal

from grayven.exceptions import ServiceError
from grayven.grand_comics_database import GrandComicsDatabase as Grayven
from grayven.schemas.issue import Issue
from grayven.schemas.series import Series
from grayven.sqlite_cache import SQLiteCache
from natsort import humansorted, ns
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_root
from perdoo.console import CONSOLE, create_menu
from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.services._base import BaseService
from perdoo.utils import IssueSearch, Search, SeriesSearch

LOGGER = logging.getLogger(__name__)


class GrandComicsDatabase(BaseService[Series, Issue]):
    def __init__(self) -> None:
        cache = SQLiteCache(path=get_cache_root() / "grayven.sqlite", expiry=14)
        self.session = Grayven(cache=cache)

    def _search_series(self, name: str | None, volume: int | None, year: int | None) -> int | None:
        name = name or Prompt.ask("Series Name", console=CONSOLE)
        try:
            options = sorted(
                self.session.list_series(name=name, year=year), key=lambda x: (x.name, x.year_began)
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Series with the Name and Year: '%s %s'", name, year
                )
            search = name
            if volume:
                search += f" v{volume}"
            if year:
                search += f" ({year})"
            index = create_menu(
                options=[
                    f"{x.id} | {x.name} ({x.year_began} - {x.year_ended})"
                    if x.year_ended
                    else f"{x.id} | {x.name} ({x.year_began})"
                    for x in options
                ],
                title="GCD Series",
                subtitle=f"Searching for Series '{search}'",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if year:
                LOGGER.info("Searching again without the Year")
                return self._search_series(name=name, volume=volume, year=None)
            if Confirm.ask("Search Again", console=CONSOLE):
                return self._search_series(name=None, volume=None, year=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_series(self, search: SeriesSearch) -> Series | None:
        series_id = search.grand_comics_database or self._search_series(
            name=search.name, volume=search.volume, year=search.year
        )
        if not series_id:
            return None
        try:
            series = self.session.get_series(id=series_id)
            series.grand_comics_database = series_id
            return series
        except ServiceError:
            LOGGER.exception("")
            return None

    def _search_issue(self, series_id: int, number: str | None) -> int | None:
        try:
            series = self.session.get_series(id=series_id)
            series_name, series_year = series.name, series.year_began
        except ServiceError:
            LOGGER.exception("")
            return None
        number = number or Prompt.ask("Issue Number", console=CONSOLE)
        try:
            options = humansorted(
                self.session.list_issues(
                    series_name=series_name, year=series_year, issue_number=number
                ),
                key=lambda x: (x.series_name, x.descriptor),
                alg=ns.NA | ns.G,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Issues with the Series Name, Series Year, and Number: '%s %s %s'",
                    series_name,
                    series_year,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.series_name} | {x.descriptor}" for x in options],
                title="GCD Issues",
                subtitle=f"Searching for Issue #{number}" if number else "",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if Confirm.ask("Search Again", console=CONSOLE):
                return self._search_issue(series_id=series_id, number=None)
            return None
        except ServiceError:
            LOGGER.exception("")
            return None

    def fetch_issue(self, series_id: int, search: IssueSearch) -> Issue | None:
        issue_id = search.grand_comics_database or self._search_issue(
            series_id=series_id, number=search.number
        )
        if not issue_id:
            return None
        try:
            issue = self.session.get_issue(id=issue_id)
            search.grand_comics_database = issue_id
            return issue
        except ServiceError:
            LOGGER.exception("")
            return None

    def _process_metron_info(self, series: Series, issue: Issue) -> MetronInfo | None:
        from perdoo.metadata.metron_info import (
            GTIN,
            Credit,
            Id,
            InformationSource,
            Price,
            Publisher,
            Resource,
            Role,
            Series,
            Url,
        )

        def parse_prices(price_str: str) -> list[Price]:
            prices = []
            for price in price_str.split(";"):
                value, country = price.strip().split()
                prices.append(Price(value=Decimal(value), country=country))
            return prices

        try:
            publisher = self.session.get_publisher(id=series.publisher_id)
        except ServiceError:
            publisher = None

        credits = {}  # noqa: A001
        for story in issue.story_set:
            for creator in story.script.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.SCRIPT)
            for creator in story.pencils.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.PENCILLER)
            for creator in story.inks.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.INKER)
            for creator in story.colors.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.COLORIST)
            for creator in story.letters.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.LETTERER)
            for creator in story.editing.split(";"):
                if creator.strip() not in credits:
                    credits[creator.strip()] = []
                credits[creator.strip()].append(Role.EDITOR)
        return MetronInfo(
            characters=[
                Resource[str](value=x)
                for story in issue.story_set
                for x in story.characters.split(";")
                if story.characters
            ],
            credits=[
                Credit(creator=Resource[str](value=key), roles=value)
                for key, value in credits.items()
            ],
            genres=[
                Resource[str](value=x)
                for story in issue.story_set
                for x in story.genre.split(";")
                if story.genre
            ],
            gtin=GTIN(isbn=issue.isbn, upc=issue.barcode) if issue.isbn or issue.barcode else None,
            ids=[
                Id(
                    source=InformationSource.GRAND_COMICS_DATABASE,
                    value=str(issue.id),
                    primary=True,
                )
            ],
            last_modified=datetime.now(),
            page_count=int(issue.page_count),
            prices=parse_prices(issue.price),
            publisher=Publisher(
                id=str(series.publisher_id), name=publisher.name if publisher else None
            ),
            series=Series(
                id=str(series.id),
                lang=series.language,
                name=series.name,
                start_year=series.year_began,
            ),
            store_date=issue.on_sale_date,
            urls=[Url(primary=True, value=f"https://www.comics.org/issue/{issue.id}/")],
        )

    def _process_comic_info(self, series: Series, issue: Issue) -> ComicInfo | None:
        comic_info = ComicInfo()

        comic_info.character_list = [x for story in issue.story_set for x in story.characters.split(";") if story.characters]
        comic_info.credits = {
            "Writer": [x.strip() for story in issue.story_set for x in story.script.split(";") if story.script],
            "Penciller": [x.strip() for story in issue.story_set for x in story.pencils.split(";") if story.pencils],
            "Inker": [x.strip() for story in issue.story_set for x in story.inks.split(";") if story.inks],
            "Colorist": [x.strip() for story in issue.story_set for x in story.colors.split(";") if story.colors],
            "Letterer": [x.strip() for story in issue.story_set for x in story.letters.split(";") if story.letters],
            "Editor": [x.strip() for story in issue.story_set for x in story.editing.split(";") if story.editing],
        }

        return comic_info

    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]:
        if not search.series.grand_comics_database and search.issue.grand_comics_database:
            try:
                temp = self.session.get_issue(id=search.issue.grand_comics_database)
                if match := re.search(r"/series/(\d+)/", str(temp.series)):
                    search.series.grand_comics_database = int(match.group(1))
            except ServiceError:
                pass

        series = self.fetch_series(search=search.series)
        if not series:
            return None, None
        issue = self.fetch_issue(series_id=series.id, search=search.issue)
        if not issue:
            return None, None

        metron_info = self._process_metron_info(series=series, issue=issue)
        comic_info = self._process_comic_info(series=series, issue=issue)
        return metron_info, comic_info
