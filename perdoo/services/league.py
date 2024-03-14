from __future__ import annotations

__all__ = ["League"]

import logging

from himon.league_of_comic_geeks import LeagueofComicGeeks as Himon
from himon.sqlite_cache import SQLiteCache

from perdoo import get_cache_dir
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
