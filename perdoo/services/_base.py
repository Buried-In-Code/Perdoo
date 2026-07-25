__all__ = ["BaseService"]

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from prompt_toolkit.styles import Style
from questionary import Choice, select

from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.utils import IssueSearch, Search, SeriesSearch

S = TypeVar("S")
C = TypeVar("C")
DEFAULT_CHOICE = Choice(title="None of the Above", value=None)


class BaseService(ABC, Generic[S, C]):
    @staticmethod
    def _prompt_select(message: str, choices: list[Choice]) -> Any:  # noqa: ANN401
        if not choices:
            return None
        selected = select(
            message,
            default=DEFAULT_CHOICE,
            choices=[*choices, DEFAULT_CHOICE],
            style=Style([("dim", "dim")]),
        ).ask()
        if select and selected != DEFAULT_CHOICE.title:
            return selected
        return None

    @abstractmethod
    def _search_series(
        self, name: str | None, volume: int | None, year: int | None, filename: str
    ) -> int | None: ...

    @abstractmethod
    def fetch_series(self, search: SeriesSearch, filename: str) -> S | None: ...

    @abstractmethod
    def _search_issue(self, series_id: int, number: str | None, filename: str) -> int | None: ...

    @abstractmethod
    def fetch_issue(self, series_id: int, search: IssueSearch, filename: str) -> C | None: ...

    @abstractmethod
    def _process_metron_info(self, series: S, issue: C) -> MetronInfo | None: ...

    @abstractmethod
    def _process_comic_info(self, series: S, issue: C) -> ComicInfo | None: ...

    @abstractmethod
    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]: ...
