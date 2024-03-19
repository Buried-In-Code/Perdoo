from __future__ import annotations

__all__ = ["League"]

import logging

from himon.league_of_comic_geeks import LeagueofComicGeeks as Himon
from himon.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
from perdoo.models import ComicInfo, Metadata, MetronInfo
from perdoo.settings import LeagueofComicGeeks as LeagueSettings

LOGGER = logging.getLogger(__name__)


class League:
    def __init__(self: League, settings: LeagueSettings):
        cache = SQLiteCache(path=get_cache_dir() / "himon.sqlite", expiry=14)
        self.himon = Himon(
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            access_token=settings.access_token,
            cache=cache,
        )
        if not settings.access_token:
            LOGGER.info("Generating new access token")
            self.himon.access_token = settings.access_token = self.himon.generate_access_token()

    def fetch(
        self: League,
        metadata: Metadata,  # noqa: ARG002
        metron_info: MetronInfo,  # noqa: ARG002
        comic_info: ComicInfo,  # noqa: ARG002
    ) -> bool:
        return False
