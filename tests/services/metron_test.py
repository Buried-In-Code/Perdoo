from unittest.mock import MagicMock, patch

import pytest
from mokkari.schemas.issue import Issue
from mokkari.schemas.series import Series
from rich.prompt import Confirm

from perdoo.services.metron import DEFAULT_CHOICE, Metron
from perdoo.settings import Metron as MetronSettings
from perdoo.utils import IssueSearch, SeriesSearch


@pytest.fixture
def service() -> Metron:
    settings = MetronSettings(username="username", password="password")  # noqa: S106
    return Metron(settings=settings)


@pytest.fixture
def series_mock() -> Series:
    return MagicMock()


@pytest.fixture
def issue_mock() -> Issue:
    return MagicMock()


@pytest.mark.parametrize(("data", "expected"), [(None, None)])
def test_search_series_by_comicvine(
    service: Metron, data: int | None, expected: int | None
) -> None:
    pass


def test_search_series(service: Metron, series_mock: Series) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[series_mock]),
        patch("perdoo.services.metron.select") as select_mock,
    ):
        select_mock.return_value.ask.return_value = series_mock
        found = service._search_series(name="Venom", volume=None, year=None)  # noqa: SLF001
    assert found == series_mock.id


def test_search_series_default(service: Metron, series_mock: Series) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[series_mock, series_mock]),
        patch("perdoo.services.metron.select") as select_mock,
        patch.object(Confirm, "ask", return_value=False),
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        found = service._search_series(name="Venom", volume=None, year=None)  # noqa: SLF001
    assert found is None


def test_search_series_no_results(service: Metron) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[]),
        patch.object(Confirm, "ask", return_value=False),
    ):
        found = service._search_series(name="Venom", volume=None, year=None)  # noqa: SLF001
    assert found is None


def test_fetch_series(service: Metron, series_mock: Series) -> None:
    with patch.object(service.session, "series", return_value=series_mock):
        mock_search = SeriesSearch(name="Venom", metron=series_mock.id)
        found = service.fetch_series(search=mock_search)
    assert found == series_mock


@pytest.mark.parametrize(("data", "expected"), [(None, None)])
def test_search_issue_by_comicvine(service: Metron, data: int | None, expected: int | None) -> None:
    pass


def test_search_issues(service: Metron, issue_mock: Issue) -> None:
    with (
        patch.object(service.session, "issues_list", return_value=[issue_mock]),
        patch("perdoo.services.metron.select") as mock_select,
    ):
        mock_select.return_value.ask.return_value = issue_mock
        found = service._search_issue(series_id=466, number="1")  # noqa: SLF001
    assert found == issue_mock.id


def test_search_issues_default(service: Metron, issue_mock: Issue) -> None:
    with (
        patch.object(service.session, "issues_list", return_value=[issue_mock, issue_mock]),
        patch("perdoo.services.metron.select") as select_mock,
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        found = service._search_issue(series_id=466, number="1")  # noqa: SLF001
    assert found is None


def test_search_issues_no_results(service: Metron) -> None:
    with patch.object(service.session, "issues_list", return_value=[]):
        found = service._search_issue(series_id=466, number="1")  # noqa: SLF001
    assert found is None


def test_fetch_issue(service: Metron, issue_mock: Issue) -> None:
    with patch.object(service.session, "issue", return_value=issue_mock):
        mock_search = IssueSearch(metron=issue_mock.id)
        found = service.fetch_issue(series_id=466, search=mock_search)
    assert found == issue_mock
