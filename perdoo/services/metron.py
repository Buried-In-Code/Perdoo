from __future__ import annotations

__all__ = ["Metron"]

import logging

from mokkari.exceptions import ApiError
from mokkari.issue import Issue
from mokkari.publisher import Publisher
from mokkari.series import Series
from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache
from rich.prompt import Confirm, Prompt

from perdoo import get_cache_dir
from perdoo.console import CONSOLE, create_menu
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.models.metadata import Source
from perdoo.models.metron_info import InformationSource
from perdoo.services import BaseService
from perdoo.settings import Metron as MetronSettings

LOGGER = logging.getLogger(__name__)


def add_publisher_to_metadata(publisher: Publisher, metadata: Metadata) -> None: ...
def add_publisher_to_metron_info(publisher: Publisher, metron_info: MetronInfo) -> None: ...
def add_publisher_to_comic_info(publisher: Publisher, comic_info: ComicInfo) -> None: ...


def add_series_to_metadata(series: Series, metadata: Metadata) -> None: ...
def add_series_to_metron_info(series: Series, metron_info: MetronInfo) -> None: ...
def add_series_to_comic_info(series: Series, comic_info: ComicInfo) -> None: ...


def add_issue_to_metadata(issue: Issue, metadata: Metadata) -> None: ...
def add_issue_to_metron_info(issue: Issue, metron_info: MetronInfo) -> None: ...
def add_issue_to_comic_info(issue: Issue, comic_info: ComicInfo) -> None: ...


class Metron(BaseService[Publisher, Series, Issue]):
    def __init__(self: Metron, settings: MetronSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.session = Mokkari(username=settings.username, passwd=settings.password, cache=cache)

    def _get_publisher(self: Metron, comicvine_id: int) -> int | None:
        try:
            publisher = self.session.publishers_list({"cv_id": comicvine_id})
            if publisher and len(publisher) >= 1:
                return publisher[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_publishers(self: Metron, title: str | None) -> int | None:
        title = title or Prompt.ask("Publisher title", console=CONSOLE)
        try:
            options = sorted(
                self.session.publishers_list(params={"name": title}), key=lambda x: x.name
            )
            if not options:
                LOGGER.warning("Unable to find any publishers with the title: '%s'", title)
            index = create_menu(
                options=[f"{x.id} | {x.name}" for x in options],
                title="Metron Publisher",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_publishers(title=None)
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_publisher_id(self: Metron, metadata: Metadata, metron_info: MetronInfo) -> int | None:
        publisher_id = next(
            (
                x.value
                for x in metadata.issue.series.publisher.resources
                if x.source == Source.METRON
            ),
            None,
        ) or (
            metron_info.publisher.id
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not publisher_id:
            comicvine_id = next(
                (
                    x.value
                    for x in metadata.issue.series.publisher.resources
                    if x.source == Source.COMICVINE
                ),
                None,
            ) or (
                metron_info.publisher.id
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                publisher_id = self._get_publisher(comicvine_id=comicvine_id)
        return publisher_id or self._search_publishers(title=metadata.issue.series.publisher.title)

    def fetch_publisher(
        self: Metron, metadata: Metadata, metron_info: MetronInfo, comic_info: ComicInfo
    ) -> Publisher | None:
        publisher_id = self._get_publisher_id(metadata=metadata, metron_info=metron_info)
        if not publisher_id:
            return None
        try:
            publisher = self.session.publisher(_id=publisher_id)
            add_publisher_to_metadata(publisher=publisher, metadata=metadata)
            add_publisher_to_metron_info(publisher=publisher, metron_info=metron_info)
            add_publisher_to_comic_info(publisher=publisher, comic_info=comic_info)
            return publisher
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_series(self: Metron, comicvine_id: int) -> int | None:
        try:
            series = self.session.series_list({"cv_id": comicvine_id})
            if series and len(series) >= 1:
                return series[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_series(self: Metron, publisher_id: int, title: str | None) -> int | None:
        title = title or Prompt.ask("Series title", console=CONSOLE)
        try:
            options = sorted(
                self.session.series_list(params={"publisher_id": publisher_id, "name": title}),
                key=lambda x: x.series,
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Series with a PublisherId: %s and the title: '%s'",
                    publisher_id,
                    title,
                )
            index = create_menu(
                options=[f"{x.id} | {x.series}" for x in options],
                title="Metron Series",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if not Confirm.ask("Try Again", console=CONSOLE):
                return None
            return self._search_series(publisher_id=publisher_id, title=None)
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_series_id(
        self: Metron, publisher_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None:
        series_id = next(
            (x.value for x in metadata.issue.series.resources if x.source == Source.METRON), None
        ) or (
            metron_info.series.id
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not series_id:
            comicvine_id = next(
                (x.value for x in metadata.issue.series.resources if x.source == Source.COMICVINE),
                None,
            ) or (
                metron_info.series.id
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                series_id = self._get_series(comicvine_id=comicvine_id)
        return series_id or self._search_series(
            publisher_id=publisher_id, title=metadata.issue.series.title
        )

    def fetch_series(
        self: Metron,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        publisher_id: int,
    ) -> Series | None:
        series_id = self._get_series_id(
            publisher_id=publisher_id, metadata=metadata, metron_info=metron_info
        )
        if not series_id:
            return None
        try:
            series = self.session.series(_id=series_id)
            add_series_to_metadata(series=series, metadata=metadata)
            add_series_to_metron_info(series=series, metron_info=metron_info)
            add_series_to_comic_info(series=series, comic_info=comic_info)
            return series
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue(self: Metron, comicvine_id: int) -> int | None:
        try:
            issue = self.session.issues_list({"cv_id": comicvine_id})
            if issue and len(issue) >= 1:
                return issue[0].id
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _search_issues(self: Metron, series_id: int, number: str | None) -> int | None:
        try:
            options = sorted(
                self.session.issues_list(
                    {"filter": f"series_id:{series_id},number:{number}"}
                    if number
                    else {"filter": f"series_id:{series_id}"}
                ),
                key=lambda x: (x.issue),
            )
            if not options:
                LOGGER.warning(
                    "Unable to find any Issues with a SeriesId: %s and number: '%s'",
                    series_id,
                    number,
                )
            index = create_menu(
                options=[f"{x.id} | {x.issue}" for x in options],
                title="Metron Issue",
                default="None of the Above",
            )
            if index != 0:
                return options[index - 1].id
            if number:
                LOGGER.info("Searching again without the issue number")
                return self._search_issues(series_id=series_id, number=None)
            return None
        except ApiError:
            LOGGER.exception("")
            return None

    def _get_issue_id(
        self: Metron, series_id: int, metadata: Metadata, metron_info: MetronInfo
    ) -> int | None:
        issue_id = next(
            (x.value for x in metadata.issue.resources if x.source == Source.METRON), None
        ) or (
            metron_info.id.value
            if metron_info.id and metron_info.id.source == InformationSource.METRON
            else None
        )
        if not issue_id:
            comicvine_id = next(
                (x.value for x in metadata.issue.resources if x.source == Source.COMICVINE), None
            ) or (
                metron_info.id.value
                if metron_info.id and metron_info.id.source == InformationSource.COMIC_VINE
                else None
            )
            if comicvine_id:
                issue_id = self._get_issue(comicvine_id=comicvine_id)
        return issue_id or self._search_issues(series_id=series_id, number=metadata.issue.number)

    def fetch_issue(
        self: Metron,
        metadata: Metadata,
        metron_info: MetronInfo,
        comic_info: ComicInfo,
        series_id: int,
    ) -> Issue | None:
        issue_id = self._get_issue_id(
            series_id=series_id, metadata=metadata, metron_info=metron_info
        )
        if not issue_id:
            return None
        try:
            issue = self.session.issue(_id=issue_id)
            add_issue_to_metadata(issue=issue, metadata=metadata)
            add_issue_to_metron_info(issue=issue, metron_info=metron_info)
            add_issue_to_comic_info(issue=issue, comic_info=comic_info)
            return issue
        except ApiError:
            LOGGER.exception("")
            return None

    def fetch(
        self: Metron, metadata: Metadata, metron_info: MetronInfo, comic_info: ComicInfo
    ) -> bool:
        publisher = self.fetch_publisher(
            metadata=metadata, metron_info=metron_info, comic_info=comic_info
        )
        if not publisher:
            return False
        series = self.fetch_series(
            metadata=metadata,
            metron_info=metron_info,
            comic_info=comic_info,
            publisher_id=publisher.id,
        )
        if not series:
            return False
        issue = self.fetch_issue(
            metadata=metadata, metron_info=metron_info, comic_info=comic_info, series_id=series.id
        )
        if not issue:
            return False
        return True
