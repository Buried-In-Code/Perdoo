from collections.abc import Sequence
from typing import Self

import pytest
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Format, InformationSource, Series

from perdoo.services import Fetcher, MetadataResult, Prompts, Provider, Query
from perdoo.services._provider import Candidate, IssueQuery, ProviderError, SeriesQuery
from perdoo.settings import Service, Settings


class FakeProvider(Provider[str, str]):
    service = Service.METRON
    source = InformationSource.METRON
    series_filters = ("year", "volume")
    series_by_query: dict[SeriesQuery, list[Candidate]]
    issues_by_query: dict[IssueQuery, list[Candidate]]

    def __init__(self) -> None:
        self.series_by_query = {}
        self.issues_by_query = {}
        self.broken: set[int] = set()
        self.cross_series: int | None = None
        self.cross_issue: int | None = None
        self.cover_candidates: list[Candidate] = []
        self.calls: list[tuple] = []
        self.issue_series = {10: 1, 20: 2}

    @classmethod
    def from_settings(cls, settings: Settings) -> Self | None:  # noqa: ARG003
        return cls()

    def find_series(self, query: SeriesQuery) -> Sequence[Candidate]:
        self.calls.append(("find_series", query))
        return self.series_by_query.get(query, [])

    def find_issues(self, query: IssueQuery) -> Sequence[Candidate]:
        self.calls.append(("find_issues", query))
        return self.issues_by_query.get(query, [])

    def get_series(self, series_id: int) -> str:
        self.calls.append(("get_series", series_id))
        if series_id in self.broken:
            raise ProviderError(f"series {series_id} is gone")
        return f"series-{series_id}"

    def get_issue(self, issue_id: int) -> str:
        self.calls.append(("get_issue", issue_id))
        if issue_id in self.broken:
            raise ProviderError(f"issue {issue_id} is gone")
        return f"issue-{issue_id}"

    def series_id_of(self, issue: str) -> int:
        return self.issue_series[int(issue.removeprefix("issue-"))]

    def build(self, series: str, issue: str, format_: Format | None) -> MetadataResult:
        title = f"{series}/{issue}/{format_.value if format_ else None}"
        return MetadataResult(
            comic_info=ComicInfo(title=title),
            metron_info=MetronInfo(series=Series(name=series, volume=1), number="1"),
        )

    def lookup_series(self, query: Query) -> int | None:  # noqa: ARG002
        self.calls.append(("lookup_series",))
        return self.cross_series

    def lookup_issue(self, query: Query) -> int | None:  # noqa: ARG002
        self.calls.append(("lookup_issue",))
        return self.cross_issue

    def find_by_cover(self, query: Query) -> Sequence[Candidate]:  # noqa: ARG002
        self.calls.append(("find_by_cover",))
        return self.cover_candidates

    def count(self, name: str) -> int:
        return sum(1 for call in self.calls if call[0] == name)


class FakePrompts(Prompts):
    def __init__(
        self,
        picks: Sequence[int | None] = (),
        confirms: Sequence[bool] = (),
        texts: Sequence[str | None] = (),
        format_: Format | None = None,
    ) -> None:
        self.picks, self.confirms, self.texts = list(picks), list(confirms), list(texts)
        self.format_ = format_
        self.messages: list[str] = []

    def select(self, message: str, candidates: Sequence[Candidate]) -> Candidate | None:
        self.messages.append(message)
        pick = self.picks.pop(0) if self.picks else None
        return None if pick is None else candidates[pick]

    def select_format(self) -> Format | None:
        return self.format_

    def confirm(self, message: str) -> bool:  # noqa: ARG002
        return self.confirms.pop(0) if self.confirms else False

    def text(self, message: str) -> str | None:  # noqa: ARG002
        return self.texts.pop(0) if self.texts else None


def candidate(id_: int, title: str = "x") -> Candidate:
    return Candidate(id=id_, title=title, url=f"https://example.com/{id_}")


def make_query(**kwargs: object) -> Query:
    return Query(**{"filename": "Spider 001", "name": "Spider", "number": "1", **kwargs})  # ty: ignore[invalid-argument-type]


def title_of(result: MetadataResult | None) -> str | None:
    return result.comic_info.title if result else None


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


def test_searches_by_name_then_by_issue_number(provider: FakeProvider) -> None:
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(1)]
    provider.issues_by_query[IssueQuery(1, "1")] = [candidate(10)]

    result = Fetcher(provider, FakePrompts(picks=[0, 0])).fetch(make_query())

    assert title_of(result) == "series-1/issue-10/None"


def test_known_ids_are_used_without_searching_or_prompting(provider: FakeProvider) -> None:
    query = make_query()
    query.ids_for(Service.METRON).series = 1
    query.ids_for(Service.METRON).issue = 10
    prompts = FakePrompts()

    result = Fetcher(provider, prompts).fetch(query)

    assert title_of(result) == "series-1/issue-10/None"
    assert prompts.messages == []
    assert provider.count("find_series") == provider.count("find_issues") == 0


def test_a_stale_known_id_falls_back_to_searching(provider: FakeProvider) -> None:
    provider.broken.add(99)
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(1)]
    provider.issues_by_query[IssueQuery(1, "1")] = [candidate(10)]
    query = make_query()
    query.ids_for(Service.METRON).series = 99

    result = Fetcher(provider, FakePrompts(picks=[0, 0])).fetch(query)

    assert title_of(result) == "series-1/issue-10/None"


def test_filters_are_dropped_one_at_a_time_until_something_matches(provider: FakeProvider) -> None:
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(1)]
    provider.issues_by_query[IssueQuery(1, "1")] = [candidate(10)]

    Fetcher(provider, FakePrompts(picks=[0, 0])).fetch(make_query(volume=2, year=2020))

    searches = [call[1] for call in provider.calls if call[0] == "find_series"]
    assert searches == [
        SeriesQuery("Spider", volume=2, year=2020),
        SeriesQuery("Spider", volume=2),
        SeriesQuery("Spider"),
    ]


def test_search_again_asks_for_a_new_name_and_resets_the_filters(provider: FakeProvider) -> None:
    provider.series_by_query[SeriesQuery("Spider-Man")] = [candidate(1)]
    provider.issues_by_query[IssueQuery(1, "1")] = [candidate(10)]
    prompts = FakePrompts(picks=[0, 0], confirms=[True], texts=["Spider-Man"])

    result = Fetcher(provider, prompts).fetch(make_query(volume=2, year=2020))

    assert title_of(result) == "series-1/issue-10/None"


def test_declining_every_option_ends_the_search(provider: FakeProvider) -> None:
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(1)]

    assert Fetcher(provider, FakePrompts(picks=[None])).fetch(make_query()) is None


def test_issue_search_retries_without_the_number(provider: FakeProvider) -> None:
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(1)]
    provider.issues_by_query[IssueQuery(1)] = [candidate(10)]

    result = Fetcher(provider, FakePrompts(picks=[0, 0])).fetch(make_query())

    assert title_of(result) == "series-1/issue-10/None"
    issue_searches = [call[1] for call in provider.calls if call[0] == "find_issues"]
    assert issue_searches == [IssueQuery(1, "1"), IssueQuery(1)]


def test_cross_references_are_used_before_asking_the_user(provider: FakeProvider) -> None:
    provider.cross_series = 1
    provider.issues_by_query[IssueQuery(1, "1")] = [candidate(10)]
    prompts = FakePrompts(picks=[0])

    result = Fetcher(provider, prompts).fetch(make_query())

    assert title_of(result) == "series-1/issue-10/None"
    assert provider.count("find_series") == 0
    assert len(prompts.messages) == 1


def test_cover_match_finds_the_series_and_fetches_the_issue_once(provider: FakeProvider) -> None:
    provider.cover_candidates = [candidate(20)]

    result = Fetcher(provider, FakePrompts(picks=[0])).fetch(make_query())

    assert title_of(result) == "series-2/issue-20/None"
    assert provider.count("get_issue") == 1
    assert provider.count("find_series") == 0


def test_the_cover_is_only_hashed_when_a_provider_needs_it() -> None:
    def explode() -> str:
        raise AssertionError("cover hash should not be computed")

    provider = FakeProvider()
    query = make_query(cover_source=explode)
    query.ids_for(Service.METRON).series = 1
    query.ids_for(Service.METRON).issue = 10

    assert Fetcher(provider, FakePrompts()).fetch(query) is not None


def test_provider_errors_are_reported_without_raising(provider: FakeProvider) -> None:
    def fail(_: SeriesQuery) -> Sequence[Candidate]:
        raise ProviderError("boom")

    provider.find_series = fail  # ty: ignore[invalid-assignment]

    assert Fetcher(provider, FakePrompts()).fetch(make_query()) is None


@pytest.mark.parametrize(
    ("provides_format", "expected"), [(True, "None"), (False, Format.ANNUAL.value)]
)
def test_the_format_prompt_only_applies_to_providers_without_a_format(
    provider: FakeProvider, provides_format: bool, expected: str
) -> None:
    provider.provides_format = provides_format
    query = make_query()
    query.ids_for(Service.METRON).series = 1
    query.ids_for(Service.METRON).issue = 10
    prompts = FakePrompts(format_=Format.ANNUAL)

    result = Fetcher(provider, prompts, ask_format=True).fetch(query)

    assert title_of(result) == f"series-1/issue-10/{expected}"


def test_resolution_order_is_issue_first_then_series_then_issue_search(
    provider: FakeProvider,
) -> None:
    provider.broken |= {5, 6}
    query = make_query()
    query.ids_for(Service.METRON).series = 5
    query.ids_for(Service.METRON).issue = 6

    Fetcher(provider, FakePrompts()).fetch(query)

    assert [call[0] for call in provider.calls] == [
        "get_issue",  # issue id
        "lookup_issue",  # foreign issue id
        "find_by_cover",  # cover hash
        "get_series",  # series id
        "lookup_series",  # foreign series id
        "find_series",  # series search
    ]


def test_the_issue_id_decides_the_series(provider: FakeProvider) -> None:
    query = make_query()
    query.ids_for(Service.METRON).series = 99
    query.ids_for(Service.METRON).issue = 10

    result = Fetcher(provider, FakePrompts()).fetch(query)

    assert title_of(result) == "series-1/issue-10/None"
    assert ("get_series", 99) not in provider.calls


def test_a_foreign_issue_id_decides_the_series_and_stops_the_search(provider: FakeProvider) -> None:
    provider.cross_issue = 20

    result = Fetcher(provider, FakePrompts()).fetch(make_query())

    assert title_of(result) == "series-2/issue-20/None"
    assert provider.count("find_by_cover") == 0


def test_a_cover_match_beats_a_known_series_id(provider: FakeProvider) -> None:
    provider.cover_candidates = [candidate(20)]
    query = make_query()
    query.ids_for(Service.METRON).series = 5

    result = Fetcher(provider, FakePrompts(picks=[0])).fetch(query)

    assert title_of(result) == "series-2/issue-20/None"
    assert ("get_series", 5) not in provider.calls


def test_a_series_without_the_issue_falls_through_to_the_next_series(
    provider: FakeProvider,
) -> None:
    provider.series_by_query[SeriesQuery("Spider")] = [candidate(2)]
    provider.issues_by_query[IssueQuery(2, "1")] = [candidate(20)]
    query = make_query()
    query.ids_for(Service.METRON).series = 1

    result = Fetcher(provider, FakePrompts(picks=[0, 0])).fetch(query)

    assert title_of(result) == "series-2/issue-20/None"
    assert [call[0] for call in provider.calls if call[0].startswith("find_")] == [
        "find_by_cover",
        "find_issues",  # series 1, with the number
        "find_issues",  # series 1, without it
        "find_series",
        "find_issues",
    ]
