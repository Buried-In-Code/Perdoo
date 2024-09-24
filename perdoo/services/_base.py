__all__ = ["BaseService"]

from abc import abstractmethod
from typing import Generic, TypeVar

from perdoo.models import ComicInfo, MetronInfo
from perdoo.utils import Details

S = TypeVar("S")
C = TypeVar("C")


class BaseService(Generic[S, C]):
    @abstractmethod
    def _get_series_id(self, title: str | None) -> int | None: ...

    @abstractmethod
    def fetch_series(self, details: Details) -> S | None: ...

    @abstractmethod
    def _get_issue_id(self, series_id: int, number: str | None) -> int | None: ...

    @abstractmethod
    def fetch_issue(self, series_id: int, details: Details) -> C | None: ...

    @abstractmethod
    def _process_metron_info(self, series: S, issue: C) -> MetronInfo | None: ...

    @abstractmethod
    def _process_comic_info(self, series: S, issue: C) -> ComicInfo | None: ...

    @abstractmethod
    def fetch(self, details: Details) -> tuple[MetronInfo | None, ComicInfo | None]: ...
