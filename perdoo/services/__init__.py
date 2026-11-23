__all__ = [
    "PROVIDERS",
    "Fetcher",
    "MetadataResult",
    "Prompts",
    "Provider",
    "Query",
    "build_fetchers",
    "build_query",
]

from typing import Any

from shortbox import Comic

from perdoo.services._fetcher import Fetcher
from perdoo.services._models import MetadataResult, Query
from perdoo.services._prompts import Prompts
from perdoo.services._provider import Provider
from perdoo.services.comicvine import Comicvine
from perdoo.services.metron import Metron
from perdoo.settings import Settings

PROVIDERS: tuple[type[Provider[Any, Any]], ...] = (Metron, Comicvine)


def build_fetchers(settings: Settings, ask_format: bool = False) -> list[Fetcher[Any, Any]]:
    available = {cls.service: cls for cls in PROVIDERS}
    return [
        Fetcher(provider, ask_format=ask_format)
        for service in settings.services.order
        if (cls := available.get(service)) and (provider := cls.from_settings(settings))
    ]


def build_query(comic: Comic) -> Query:
    return Query.build(comic, sources={cls.source: cls.service for cls in PROVIDERS})
