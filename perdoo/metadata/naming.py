__all__ = ["evaluate_pattern", "sanitize"]

import logging
import re
from collections.abc import Callable

from perdoo.metadata.comic_info import ComicInfo
from perdoo.metadata.metron_info import MetronInfo

LOGGER = logging.getLogger(__name__)


def sanitize(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r"[^0-9a-zA-Z&! ]+", "", value.replace("-", " "))
    value = " ".join(value.split())
    return value.replace(" ", "-")


def evaluate_pattern(
    pattern_map: dict[str, Callable[[MetronInfo | ComicInfo], str]],
    pattern: str,
    obj: MetronInfo | ComicInfo,
) -> str:
    def replace_match(match: re.Match) -> str:
        key = match.group("key")
        padding = match.group("padding")

        if key not in pattern_map:
            LOGGER.warning("Unknown pattern: %s", key)
            return key
        value = pattern_map[key](obj)

        if padding and (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
            return f"{int(value):0{padding}}"
        return sanitize(value=str(value))

    pattern_regex = re.compile(r"{(?P<key>[a-zA-Z-]+)(?::(?P<padding>\d+))?}")
    return pattern_regex.sub(replace_match, pattern)
