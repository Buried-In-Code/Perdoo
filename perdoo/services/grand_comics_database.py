__all__ = ["GrandComicsDatabase"]

import logging

from grayven.exceptions import ServiceError
from grayven.grand_comics_database import GrandComicsDatabase as Grayven
from grayven.schemas.issue import Issue
from grayven.schemas.series import Series
from grayven.sqlite_cache import SQLiteCache
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
        pass

    def _search_issue(self, series_id: int, number: str | None) -> int | None:
        pass

    def fetch_issue(self, series_id: int, search: IssueSearch) -> Issue | None:
        pass

    def _process_metron_info(self, series: Series, issue: Issue) -> MetronInfo | None:
        pass

    def _process_comic_info(self, series: Series, issue: Issue) -> ComicInfo | None:
        pass

    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]:
        pass
