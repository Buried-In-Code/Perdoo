__all__ = ["Metadata", "PascalModel", "sanitize"]

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic.alias_generators import to_pascal
from pydantic_xml import BaseXmlModel
from rich.panel import Panel

from perdoo.console import CONSOLE
from perdoo.settings import Naming
from perdoo.utils import flatten_dict

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11

LOGGER = logging.getLogger(__name__)


def sanitize(value: str | None, seperator: Literal["-", "_", ".", " "]) -> str | None:
    if not value:
        return value
    value = str(value)
    value = re.sub(r"[^0-9a-zA-Z&! ]+", "", value.replace(seperator, " "))
    value = " ".join(value.split())
    return value.replace(" ", seperator)


class PascalModel(
    BaseXmlModel,
    alias_generator=to_pascal,
    populate_by_name=True,
    str_strip_whitespace=True,
    validate_assignment=True,
    coerce_numbers_to_str=True,
    extra="ignore",
    nsmap={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    skip_empty=True,
    search_mode="unordered",
):
    pass


class Metadata(PascalModel, ABC):
    @abstractmethod
    def get_filename(self, settings: Naming) -> str: ...

    @classmethod
    def from_bytes(cls, content: bytes) -> Self:
        return cls.from_xml(content)

    def to_bytes(self) -> bytes:
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + self.to_xml(
            skip_empty=True, pretty_print=True, encoding="UTF-8"
        )

    def to_file(self, file: Path) -> None:
        file.write_bytes(self.to_bytes())

    def display(self) -> None:
        content = flatten_dict(content=self.model_dump(exclude_none=True))
        content_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]" for k, v in content.items()
        ]

        CONSOLE.print(Panel.fit("\n".join(content_vals), title=type(self).__name__))

    def evaluate_pattern(
        self,
        pattern_map: dict[str, Callable[[Self], str]],
        pattern: str,
        seperator: Literal["-", "_", ".", " "],
    ) -> str:
        def replace_match(match: re.Match) -> str:
            key = match.group("key")
            padding = match.group("padding")

            if key not in pattern_map:
                LOGGER.warning("Unknown pattern: %s", key)
                return key
            value = pattern_map[key](self)

            if padding and (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
                return f"{int(value):0{padding}}"
            return sanitize(value=value, seperator=seperator) or ""

        pattern_regex = re.compile(r"{(?P<key>[a-zA-Z-]+)(?::(?P<padding>\d+))?}")
        return pattern_regex.sub(replace_match, pattern)
