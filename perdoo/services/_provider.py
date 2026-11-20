__all__ = ["Candidate", "IssueQuery", "Provider", "ProviderError", "SeriesQuery"]

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Generic, Self, TypeVar

from shortbox.metadata.metron_info import Format, InformationSource

from perdoo.services._models import MetadataResult, Query
from perdoo.settings import Service, Settings

S = TypeVar("S")
I = TypeVar("I")  # noqa: E741


class ProviderError(Exception): ...


@dataclass(frozen=True, slots=True)
class Candidate:
    id: int
    title: str
    url: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SeriesQuery:
    name: str
    volume: int | None = None
    year: int | None = None


@dataclass(frozen=True, slots=True)
class IssueQuery:
    series_id: int
    number: str | None = None


class Provider(ABC, Generic[S, I]):
    service: ClassVar[Service]
    source: ClassVar[InformationSource]
    series_filters: ClassVar[Sequence[str]] = ()
    issue_filters: ClassVar[Sequence[str]] = ("number",)
    provides_format: ClassVar[bool] = True

    @classmethod
    @abstractmethod
    def from_settings(cls, settings: Settings) -> Self | None: ...

    @abstractmethod
    def find_series(self, query: SeriesQuery) -> Sequence[Candidate]: ...

    @abstractmethod
    def find_issues(self, query: IssueQuery) -> Sequence[Candidate]: ...

    @abstractmethod
    def get_series(self, series_id: int) -> S: ...

    @abstractmethod
    def get_issue(self, issue_id: int) -> I: ...

    @abstractmethod
    def series_id_of(self, issue: I) -> int: ...

    @abstractmethod
    def build(self, series: S, issue: I, format_: Format | None) -> MetadataResult: ...

    def lookup_series(self, query: Query) -> int | None:  # noqa: ARG002
        return None

    def lookup_issue(self, query: Query) -> int | None:  # noqa: ARG002
        return None

    def find_by_cover(self, query: Query) -> Sequence[Candidate]:  # noqa: ARG002
        return ()
