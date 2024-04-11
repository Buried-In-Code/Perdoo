from __future__ import annotations

__all__ = ["BaseService"]

from abc import abstractmethod
from typing import Generic, TypeVar

from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.utils import Details

S = TypeVar("S")
C = TypeVar("C")


class BaseService(Generic[S, C]):
    @abstractmethod
    def _get_series_id(self: BaseService, title: str) -> int | None: ...

    @abstractmethod
    def fetch_series(self: BaseService, details: Details) -> S | None: ...

    @abstractmethod
    def _get_issue_id(self: BaseService, series_id: int, number: str | None) -> int | None: ...

    @abstractmethod
    def fetch_issue(self: BaseService, series_id: int, details: Details) -> C | None: ...

    @abstractmethod
    def _process_metadata(self: BaseService, series: S, issue: C) -> Metadata | None: ...

    @abstractmethod
    def _process_metron_info(self: BaseService, series: S, issue: C) -> MetronInfo | None: ...

    @abstractmethod
    def _process_comic_info(self: BaseService, series: S, issue: C) -> ComicInfo | None: ...

    @abstractmethod
    def fetch(
        self: BaseService, details: Details
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]: ...
