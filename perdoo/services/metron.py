from __future__ import annotations

__all__ = ["Metron"]

import logging

from mokkari.session import Session as Mokkari
from mokkari.sqlite_cache import SqliteCache

from perdoo import get_cache_dir
from perdoo.settings import Metron as MetronSettings

LOGGER = logging.getLogger(__name__)


class Metron:
    def __init__(self: Metron, settings: MetronSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.session = Mokkari(username=settings.username, passwd=settings.password, cache=cache)
