from __future__ import annotations

__all__ = ["PascalModel", "InfoModel"]

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

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
    def unwrap_list(
        self: PascalModel, mappings: dict[str, str], content: dict[str, Any]
    ) -> dict[str, Any]:
        for key, value in mappings.items():
            if key in content and isinstance(content[key], dict) and value in content[key]:
                content[key] = content[key][value]
            elif key in content and not content[key]:
                content[key] = []
        return content

    def clean_contents(self: PascalModel, content: dict[str, Any]) -> dict[str, Any]:
        cleaned_content = {}
        for key, value in content.items():
            if isinstance(key, Enum):
                key = str(key)
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (Enum, int, float)):
                value = str(value)
            elif isinstance(value, dict):
                if not value:
                    continue
                value = self.clean_contents(value)
            elif isinstance(value, list):
                if not value:
                    continue
                cleaned_list = []
                for entry in value:
                    if isinstance(entry, bool):
                        entry = "true" if entry else "false"
                    elif isinstance(entry, (Enum, int, float)):
                        entry = str(entry)
                    elif isinstance(entry, dict):
                        entry = self.clean_contents(entry)
                    cleaned_list.append(entry)
                value = cleaned_list
            cleaned_content[key] = value
        return cleaned_content

    def wrap_list(
        self: PascalModel, mappings: dict[str, str], content: dict[str, Any]
    ) -> dict[str, Any]:
        for key, value in content.copy().items():
            if isinstance(value, dict):
                content[key] = self.wrap_list(mappings, value)
            elif isinstance(value, list):
                for index, entry in enumerate(value):
                    if isinstance(entry, dict):
                        content[key][index] = self.wrap_list(mappings, entry)
                if key in mappings:
                    content[key] = {mappings[key]: content[key]}
        return content

    def to_xml_text(
        self: PascalModel, mappings: list[str], content: dict[str, Any]
    ) -> dict[str, Any]:
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
    def from_bytes(cls: type[InfoModel], content: bytes) -> InfoModel: ...

    @classmethod
    def from_file(cls: type[InfoModel], file: Path) -> InfoModel:
        with file.open("rb") as stream:
            return cls.from_bytes(content=stream.read())

    @abstractmethod
    def to_file(self: InfoModel, file: Path) -> None: ...
