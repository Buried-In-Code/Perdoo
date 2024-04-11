from __future__ import annotations

__all__ = ["Marvel"]

import logging

from esak.comic import Comic
from esak.series import Series
from esak.session import Session as Esak
from esak.sqlite_cache import SqliteCache

from perdoo import get_cache_dir
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.services._base import BaseService
from perdoo.settings import Marvel as MarvelSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class Marvel(BaseService[Series, Comic]):
    def __init__(self: Marvel, settings: MarvelSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.session = Esak(
            public_key=settings.public_key, private_key=settings.private_key, cache=cache
        )

    def _get_series_id(self: Marvel, title: str) -> int | None:
        pass

    def fetch_series(self: Marvel, details: Details) -> Series | None:
        pass

    def _get_issue_id(self: Marvel, series_id: int, number: str | None) -> int | None:
        pass

    def fetch_issue(self: Marvel, series_id: int, details: Details) -> Comic | None:
        pass

    def _process_metadata(self: Marvel, series: Series, issue: Comic) -> Metadata | None:
        pass

    def _process_metron_info(self: Marvel, series: Series, issue: Comic) -> MetronInfo | None:
        pass

    def _process_comic_info(self: Marvel, series: Series, issue: Comic) -> ComicInfo | None:
        pass

    def fetch(
        self: Marvel,
        details: Details,  # noqa: ARG002
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        return None, None, None
