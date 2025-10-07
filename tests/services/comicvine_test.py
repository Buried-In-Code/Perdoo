from unittest.mock import MagicMock, patch

import pytest
from simyan.schemas.issue import Issue
from simyan.schemas.volume import Volume

from perdoo.services.comicvine import DEFAULT_CHOICE, Comicvine
from perdoo.settings import Comicvine as ComicvineSettings
from perdoo.utils import IssueSearch, SeriesSearch


@pytest.fixture
def service() -> Comicvine:
    settings = ComicvineSettings(api_key="Api-Key")
    return Comicvine(settings=settings)


@pytest.fixture
def volume_mock() -> Volume:
    return MagicMock()


@pytest.fixture
def issue_mock() -> Issue:
    return MagicMock()


def test_search_series(service: Comicvine, volume_mock: Volume) -> None:
    with (
        patch.object(service.session, "list_volumes", return_value=[volume_mock]),
        patch("perdoo.services.comicvine.select") as select_mock,
    ):
        select_mock.return_value.ask.return_value = volume_mock
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found == volume_mock.id


def test_search_series_default(service: Comicvine, volume_mock: Volume) -> None:
    with (
        patch.object(service.session, "list_volumes", return_value=[volume_mock, volume_mock]),
        patch("perdoo.services.comicvine.select") as select_mock,
        patch("perdoo.services.comicvine.confirm") as confirm_mock,
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        confirm_mock.return_value.ask.return_value = False
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found is None


def test_search_series_no_results(service: Comicvine) -> None:
    with (
        patch.object(service.session, "list_volumes", return_value=[]),
        patch("perdoo.services.comicvine.confirm") as confirm_mock,
    ):
        confirm_mock.return_value.ask.return_value = False
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found is None


def test_fetch_series(service: Comicvine, volume_mock: Volume) -> None:
    with patch.object(service.session, "get_volume", return_value=volume_mock):
        mock_search = SeriesSearch(name="Venom", comicvine=volume_mock.id)
        found = service.fetch_series(search=mock_search, filename="Venom")
    assert found == volume_mock


def test_search_issues(service: Comicvine, issue_mock: Issue) -> None:
    with (
        patch.object(service.session, "list_issues", return_value=[issue_mock]),
        patch("perdoo.services.comicvine.select") as mock_select,
    ):
        mock_select.return_value.ask.return_value = issue_mock
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found == issue_mock.id


def test_search_issues_default(service: Comicvine, issue_mock: Issue) -> None:
    with (
        patch.object(service.session, "list_issues", return_value=[issue_mock, issue_mock]),
        patch("perdoo.services.comicvine.select") as select_mock,
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found is None


def test_search_issues_no_results(service: Comicvine) -> None:
    with patch.object(service.session, "list_issues", return_value=[]):
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found is None


def test_fetch_issue(service: Comicvine, issue_mock: Issue) -> None:
    with patch.object(service.session, "get_issue", return_value=issue_mock):
        mock_search = IssueSearch(comicvine=issue_mock.id)
        found = service.fetch_issue(series_id=466, search=mock_search, filename="Venom")
    assert found == issue_mock
