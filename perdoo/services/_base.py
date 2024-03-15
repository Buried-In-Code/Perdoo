from __future__ import annotations

__all__ = ["BaseService"]

from abc import abstractmethod

from perdoo.models import ComicInfo, Metadata, MetronInfo


class BaseService:
    @abstractmethod
    def fetch(
        self: BaseService,
        metadata: Metadata | None,
        metron_info: MetronInfo | None,
        comic_info: ComicInfo | None,
    ) -> bool: ...
