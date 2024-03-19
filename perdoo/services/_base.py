from __future__ import annotations

__all__ = ["BaseService"]

from abc import abstractmethod
from typing import Generic, TypeVar

from perdoo.models import ComicInfo, Metadata, MetronInfo

P = TypeVar("P")
S = TypeVar("S")
C = TypeVar("C")


class BaseService(Generic[P, S, C]):
    @abstractmethod
    def _search_publishers(self: BaseService, title: str | None) -> int | None: ...

    @abstractmethod
    def _get_publisher_id(
        self: BaseService, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None: ...

    @abstractmethod
    def fetch_publisher(
        self: BaseService, metadata: Metadata, metron_info: MetronInfo, comic_info: ComicInfo
    ) -> P | None: ...

    @abstractmethod
    def _search_series(self: BaseService, publisher_id: int, title: str | None) -> int | None: ...

    @abstractmethod
    def _get_series_id(
        self: BaseService, publisher_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None: ...

    @abstractmethod
    def fetch_series(
        self: BaseService,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        publisher_id: int,
    ) -> S | None: ...

    @abstractmethod
    def _search_issues(self: BaseService, series_id: int, number: str | None) -> int | None: ...

    @abstractmethod
    def _get_issue_id(
        self: BaseService, series_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None: ...

    @abstractmethod
    def fetch_issue(
        self: BaseService,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        series_id: int,
    ) -> C | None: ...

    @abstractmethod
    def fetch(
        self: BaseService,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> bool: ...
