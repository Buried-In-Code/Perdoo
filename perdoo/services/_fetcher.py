__all__ = ["Fetcher"]

from collections.abc import Callable, Iterator, Sequence
from dataclasses import replace
from typing import Generic, TypeVar

from perdoo.console import CONSOLE
from perdoo.services._models import Ids, MetadataResult, Query
from perdoo.services._prompts import Prompts
from perdoo.services._provider import I, IssueQuery, Provider, ProviderError, S, SeriesQuery

T = TypeVar("T")
Q = TypeVar("Q", SeriesQuery, IssueQuery)


def _relaxed(query: Q, filters: Sequence[tuple[str, str]]) -> Iterator[tuple[Q, str | None]]:
    yield query, None
    for name, label in filters:
        if getattr(query, name):
            query = replace(query, **{name: None})
            yield query, label


class Fetcher(Generic[S, I]):
    def __init__(
        self, provider: Provider[S, I], prompts: Prompts | None = None, ask_format: bool = False
    ) -> None:
        self.provider = provider
        self.prompts = prompts or Prompts()
        self.ask_format = ask_format and not provider.provides_format
        self.name = str(provider.service)

    def fetch(self, query: Query) -> MetadataResult | None:
        ids = query.ids_for(self.provider.service)

        found = self._from_issue(query, ids) or self._from_series(query, ids)
        if not found:
            return None
        series, issue = found

        format_ = self.prompts.select_format() if self.ask_format else None
        return self.provider.build(series, issue, format_)

    def _from_issue(self, query: Query, ids: Ids) -> tuple[S, I] | None:
        for issue_id in self._distinct(
            lambda: ids.issue,
            lambda: self._guard(self.provider.lookup_issue, query),
            lambda: self._pick_by_cover(query),
        ):
            try:
                issue = self.provider.get_issue(issue_id)
                series_id = self.provider.series_id_of(issue)
                series = self.provider.get_series(series_id)
            except ProviderError as err:
                _say(query=query, message=err, style="logging.level.error")
                continue
            ids.series, ids.issue = series_id, issue_id
            return series, issue
        return None

    def _from_series(self, query: Query, ids: Ids) -> tuple[S, I] | None:
        for series_id in self._distinct(
            lambda: ids.series,
            lambda: self._guard(self.provider.lookup_series, query),
            lambda: self._search_series(query),
        ):
            try:
                series = self.provider.get_series(series_id)
                if not (issue_id := self._search_issue(query, series_id)):
                    continue
                issue = self.provider.get_issue(issue_id)
            except ProviderError as err:
                _say(query=query, message=err, style="logging.level.error")
                continue
            ids.series, ids.issue = series_id, issue_id
            return series, issue
        return None

    def _distinct(self, *sources: Callable[[], int | None]) -> Iterator[int]:
        seen: set[int] = set()
        for source in sources:
            if (found := source()) and found not in seen:
                seen.add(found)
                yield found

    def _guard(self, func: Callable[[Query], T], query: Query) -> T | None:
        try:
            return func(query)
        except ProviderError as err:
            _say(query=query, message=err, style="logging.level.error")
            return None

    def _pick_by_cover(self, query: Query) -> int | None:
        _announce(query=query)
        options = self._guard(self.provider.find_by_cover, query)
        if not options:
            return None
        message = f"Searching {self.name} for {self.provider.issue_noun} by cover"
        chosen = self.prompts.select(message, options)
        return chosen.id if chosen else None

    def _search_series(self, query: Query) -> int | None:
        noun, current = self.provider.series_noun, SeriesQuery(query.name, query.volume, query.year)
        try:
            while True:
                for attempt, dropped in _relaxed(current, self.provider.series_filters):
                    if dropped:
                        _say(
                            query=query,
                            message=f"Searching again without the {dropped}",
                            style="logging.level.info",
                        )
                    if not (options := self.provider.find_series(attempt)):
                        _say(
                            query=query,
                            message=f"Unable to find a matching {noun} on {self.name}",
                            style="logging.level.warning",
                        )
                        continue
                    if chosen := self.prompts.select(f"Searching {self.name} for {noun}", options):
                        return chosen.id
                if not self.prompts.confirm("Search Again") or not (
                    name := self.prompts.text(f"{noun} Name")
                ):
                    return None
                current = SeriesQuery(name=name)
        except ProviderError as err:
            _say(query=query, message=err, style="logging.level.error")
        return None

    def _search_issue(self, query: Query, series_id: int) -> int | None:
        noun, current = self.provider.issue_noun, IssueQuery(series_id, query.number)
        try:
            for attempt, dropped in _relaxed(current, self.provider.issue_filters):
                if dropped:
                    _say(
                        query=query,
                        message=f"Searching again without the {dropped}",
                        style="logging.level.info",
                    )
                if not (options := self.provider.find_issues(attempt)):
                    _say(
                        query=query,
                        message=f"Unable to find a matching {noun} on {self.name}",
                        style="logging.level.warning",
                    )
                    continue
                if chosen := self.prompts.select(f"Searching {self.name} for {noun}", options):
                    return chosen.id
        except ProviderError as err:
            _say(query=query, message=err, style="logging.level.error")
        return None


def _announce(query: Query) -> None:
    if not query.announced:
        query.announced = True
        CONSOLE.print(f"Syncing {query.filename!r}", style="logging.level.info")


def _say(query: Query, message: object, style: str) -> None:
    _announce(query=query)
    CONSOLE.print(message, style=style)
