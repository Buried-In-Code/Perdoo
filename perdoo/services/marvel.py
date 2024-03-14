from __future__ import annotations

__all__ = ["Marvel"]

import logging

from esak.session import Session as Esak
from esak.sqlite_cache import SqliteCache

from perdoo import get_cache_dir
from perdoo.settings import Marvel as MarvelSettings

LOGGER = logging.getLogger(__name__)


class Marvel:
    def __init__(self: Marvel, settings: MarvelSettings):
        cache = SqliteCache(db_name=str(get_cache_dir() / "mokkari.sqlite"), expire=14)
        self.esak = Esak(
            public_key=settings.public_key, private_key=settings.private_key, cache=cache
        )
