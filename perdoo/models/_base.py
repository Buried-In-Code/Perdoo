__all__ = ["PascalModel", "InfoModel"]

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel


def to_pascal_case(value: str) -> str:
    return value.replace("_", " ").title().replace(" ", "")


class PascalModel(
    BaseModel,
    alias_generator=to_pascal_case,
    populate_by_name=True,
    str_strip_whitespace=True,
    validate_assignment=True,
    extra="ignore",
):
    list_fields: ClassVar[dict[str, str]] = {}
    text_fields: ClassVar[list[str]] = []

    def __init__(self, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        self.to_xml_text(mappings=self.text_fields, content=data)
        super().__init__(**data)

    def unwrap_list(self, mappings: dict[str, str], content: dict[str, Any]) -> dict[str, Any]:
        for key, value in mappings.items():
            if key in content and isinstance(content[key], dict) and value in content[key]:
                content[key] = content[key][value]
            elif key in content and not content[key]:
                content[key] = []
        return content

    def clean_contents(self, content: dict[str, Any]) -> dict[str, Any]:
        cleaned_content = {}
        for key, value in content.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            if not value:
                continue
            if isinstance(value, dict):
                value = self.clean_contents(value)
            elif isinstance(value, list):
                clean_list = []
                for entry in value:
                    if isinstance(entry, bool):
                        clean_list.append("true" if entry else "false")
                    elif isinstance(entry, dict):
                        clean_list.append(self.clean_contents(entry))
                    else:
                        clean_list.append(str(entry))
                value = clean_list
            else:
                value = str(value)
            cleaned_content[key] = value
        return cleaned_content

    def wrap_list(self, mappings: dict[str, str], content: dict[str, Any]) -> dict[str, Any]:
        for key, value in content.copy().items():
            if not value:
                continue
            if isinstance(value, dict):
                content[key] = self.wrap_list(mappings, value)
            elif isinstance(value, list):
                for index, entry in enumerate(value):
                    if not entry:
                        continue
                    if isinstance(entry, dict):
                        content[key][index] = self.wrap_list(mappings, entry)
                if key in mappings:
                    content[key] = {mappings[key]: content[key]}
        return content

    def to_xml_text(self, mappings: list[str], content: dict[str, Any]) -> dict[str, Any]:
        for field in mappings:
            if field in content:
                if isinstance(content[field], str):
                    content[field] = {"#text": content[field]}
                elif isinstance(content[field], list):
                    for index, entry in enumerate(content[field]):
                        if isinstance(entry, str):
                            content[field][index] = {"#text": entry}
        return content


class InfoModel(ABC):
    @classmethod
    @abstractmethod
    def from_bytes(cls, content: bytes) -> "InfoModel": ...

    @classmethod
    def from_file(cls, file: Path) -> "InfoModel":
        with file.open("rb") as stream:
            return cls.from_bytes(content=stream.read())

    @abstractmethod
    def to_file(self, file: Path) -> None: ...
