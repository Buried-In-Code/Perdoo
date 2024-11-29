__all__ = ["BaseService"]

from abc import abstractmethod
from typing import Generic, TypeVar

from perdoo.metadata import ComicInfo, MetronInfo
from perdoo.utils import IssueSearch, Search, SeriesSearch

S = TypeVar("S")
C = TypeVar("C")


class BaseService(Generic[S, C]):
    @abstractmethod
    def _search_series(
        self, name: str | None, volume: int | None, year: int | None
    ) -> int | None: ...

    @abstractmethod
    def fetch_series(self, search: SeriesSearch) -> S | None: ...

    @abstractmethod
    def _search_issue(self, series_id: int, number: str | None) -> int | None: ...

    @abstractmethod
    def fetch_issue(self, series_id: int, search: IssueSearch) -> C | None: ...

    @abstractmethod
    def _process_metron_info(self, series: S, issue: C) -> MetronInfo | None: ...

    @abstractmethod
    def _process_comic_info(self, series: S, issue: C) -> ComicInfo | None: ...

    @abstractmethod
    def fetch(self, search: Search) -> tuple[MetronInfo | None, ComicInfo | None]: ...
