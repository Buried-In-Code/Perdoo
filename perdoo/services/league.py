from __future__ import annotations

__all__ = ["League"]

import logging

from himon.league_of_comic_geeks import LeagueofComicGeeks as Himon
from himon.schemas.comic import Comic
from himon.schemas.series import Series
from himon.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.services._base import BaseService
from perdoo.settings import LeagueofComicGeeks as LeagueSettings
from perdoo.utils import Details

LOGGER = logging.getLogger(__name__)


class League(BaseService[Series, Comic]):
    def __init__(self: League, settings: LeagueSettings):
        cache = SQLiteCache(path=get_cache_dir() / "himon.sqlite", expiry=14)
        self.session = Himon(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            access_token=settings.access_token,
            cache=cache,
        )
        if not settings.access_token:
            LOGGER.info("Generating new access token")
            self.session.access_token = settings.access_token = self.session.generate_access_token()

    def _get_series_id(self: League, title: str) -> int | None:
        pass

    def fetch_series(self: League, details: Details) -> Series | None:
        pass

    def _get_issue_id(self: League, series_id: int, number: str | None) -> int | None:
        pass

    def fetch_issue(self: League, series_id: int, details: Details) -> Comic | None:
        pass

    def _process_metadata(
        self: League, metadata: Metadata | None, series: Series, issue: Comic
    ) -> Metadata | None:
        pass

    def _process_metron_info(
        self: League, metron_info: MetronInfo | None, series: Series, issue: Comic
    ) -> MetronInfo | None:
        pass

    def _process_comic_info(
        self: League, comic_info: ComicInfo | None, series: Series, issue: Comic
    ) -> ComicInfo | None:
        pass

    def fetch(
        self: League,
        details: Details,  # noqa: ARG002
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> tuple[Metadata | None, MetronInfo | None, ComicInfo | None]:
        return metadata, metron_info, comic_info
