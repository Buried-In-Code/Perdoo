__all__ = ["PascalModel"]

from pathlib import Path

from pydantic_xml import BaseXmlModel

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


def to_pascal_case(value: str) -> str:
    return value.replace("_", " ").title().replace(" ", "")


class PascalModel(
    BaseXmlModel,
    alias_generator=to_pascal_case,
    populate_by_name=True,
    str_strip_whitespace=True,
    validate_assignment=True,
    extra="ignore",
    nsmap={"xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    skip_empty=True,
    search_mode="unordered",
):
    @classmethod
    def from_bytes(cls, content: bytes) -> Self:
        return cls.from_xml(content)

    def to_bytes(self) -> bytes:
        return b'<?xml version="1.0" encoding="UTF-8"?>\n' + self.to_xml(
            skip_empty=True, pretty_print=True, encoding="UTF-8"
        )

    def to_file(self, file: Path) -> None:
        file.write_bytes(self.to_bytes())
