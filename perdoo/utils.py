__all__ = [
    "IssueSearch",
    "Search",
    "SeriesSearch",
    "delete_empty_folders",
    "flatten_dict",
    "list_files",
    "sanitize",
]

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from natsort import humansorted, ns

LOGGER = logging.getLogger(__name__)


@dataclass
class SeriesSearch:
    name: str
    volume: int | None = None
    year: int | None = None
    comicvine: int | None = None
    marvel: int | None = None
    metron: int | None = None


@dataclass
class IssueSearch:
    number: str | None = None
    comicvine: int | None = None
    marvel: int | None = None
    metron: int | None = None


@dataclass
class Search:
    series: SeriesSearch
    issue: IssueSearch


def list_files(path: Path, *extensions: str) -> list[Path]:
    files = []
    for file in path.iterdir():
        if file.is_file():
            if not file.name.startswith(".") and (
                not extensions or file.suffix.lower() in extensions
            ):
                files.append(file)
        elif file.is_dir():
            files.extend(list_files(file, *extensions))
    return humansorted(files, alg=ns.NA | ns.G | ns.P)


def sanitize(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r"[^0-9a-zA-Z&! ]+", "", value.replace("-", " "))
    value = " ".join(value.split())
    return value.replace(" ", "-")


def flatten_dict(content: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    items = {}
    for key, value in content.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(flatten_dict(content=value, parent_key=new_key))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for index, entry in enumerate(value):
                items.update(flatten_dict(content=entry, parent_key=f"{new_key}[{index}]"))
        else:
            items[new_key] = value
    return dict(humansorted(items.items(), alg=ns.NA | ns.G))


def recursive_delete(path: Path) -> None:
    for item in path.iterdir():
        if item.is_dir():
            recursive_delete(item)
        else:
            item.unlink()
    path.rmdir()


def delete_empty_folders(folder: Path) -> None:
    if folder.is_dir():
        for subfolder in folder.iterdir():
            if subfolder.is_dir():
                delete_empty_folders(subfolder)
        if not any(folder.iterdir()):
            folder.rmdir()
            LOGGER.info("Deleted empty folder: %s", folder)
