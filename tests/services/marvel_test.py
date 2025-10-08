from unittest.mock import MagicMock, patch

import pytest
from esak.schemas.comic import Comic
from esak.schemas.series import Series

from perdoo.services.marvel import DEFAULT_CHOICE, Marvel
from perdoo.settings import Marvel as MarvelSettings
from perdoo.utils import IssueSearch, SeriesSearch


@pytest.fixture
def service() -> Marvel:
    settings = MarvelSettings(private_key="private-key", public_key="public-key")
    return Marvel(settings=settings)


@pytest.fixture
def series_mock() -> Series:
    return MagicMock()


@pytest.fixture
def comic_mock() -> Comic:
    return MagicMock()


def test_search_series(service: Marvel, series_mock: Series) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[series_mock]),
        patch("perdoo.services.marvel.select") as mock_select,
    ):
        mock_select.return_value.ask.return_value = series_mock
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found == series_mock.id


def test_search_series_default(service: Marvel, series_mock: Series) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[series_mock, series_mock]),
        patch("perdoo.services.marvel.select") as select_mock,
        patch("perdoo.services.marvel.confirm") as confirm_mock,
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        confirm_mock.return_value.ask.return_value = False
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found is None


def test_search_series_no_results(service: Marvel) -> None:
    with (
        patch.object(service.session, "series_list", return_value=[]),
        patch("perdoo.services.marvel.confirm") as confirm_mock,
    ):
        confirm_mock.return_value.ask.return_value = False
        found = service._search_series(name="Venom", volume=None, year=None, filename="Venom")  # noqa: SLF001
    assert found is None


def test_fetch_series(service: Marvel, series_mock: Series) -> None:
    with patch.object(service.session, "series", return_value=series_mock):
        mock_search = SeriesSearch(name="Venom", marvel=series_mock.id)
        found = service.fetch_series(search=mock_search, filename="Venom")
    assert found == series_mock


def test_search_issues(service: Marvel, comic_mock: Comic) -> None:
    with (
        patch.object(service.session, "comics_list", return_value=[comic_mock]),
        patch("perdoo.services.marvel.select") as mock_select,
    ):
        mock_select.return_value.ask.return_value = comic_mock
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found == comic_mock.id


def test_search_issues_default(service: Marvel, comic_mock: Comic) -> None:
    with (
        patch.object(service.session, "comics_list", return_value=[comic_mock, comic_mock]),
        patch("perdoo.services.marvel.select") as select_mock,
    ):
        select_mock.return_value.ask.return_value = DEFAULT_CHOICE.title
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found is None


def test_search_issues_no_results(service: Marvel) -> None:
    with patch.object(service.session, "comics_list", return_value=[]):
        found = service._search_issue(series_id=466, number="1", filename="Venom")  # noqa: SLF001
    assert found is None


def test_fetch_issue(service: Marvel, comic_mock: Comic) -> None:
    with patch.object(service.session, "comic", return_value=comic_mock):
        mock_search = IssueSearch(marvel=comic_mock.id)
        found = service.fetch_issue(series_id=466, search=mock_search, filename="Venom")
    assert found == comic_mock
