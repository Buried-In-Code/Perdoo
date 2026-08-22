__all__ = [
    "IssueSearch",
    "Search",
    "SeriesSearch",
    "delete_empty_folders",
    "display",
    "flatten_dict",
    "get_id",
    "list_files",
    "recursive_delete",
    "sanitize",
]

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from comic_archive.metadata import ComicInfo, MetronInfo
from comic_archive.metadata.metron_info import Id, InformationSource
from msgspec import to_builtins
from natsort import humansorted, ns
from rich.panel import Panel

from perdoo.console import CONSOLE

LOGGER = logging.getLogger(__name__)


@dataclass
class SeriesSearch:
    name: str
    volume: int | None = None
    year: int | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class IssueSearch:
    number: str | None = None
    comicvine: int | None = None
    metron: int | None = None


@dataclass
class Search:
    series: SeriesSearch
    issue: IssueSearch
    filename: str


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


def display(data: ComicInfo | MetronInfo, title: str | None = None) -> None:
    def encoder(obj: object) -> object:
        return str(obj) if isinstance(obj, Path) else obj

    title = title or type(data).__name__
    data_dict = flatten_dict(content=to_builtins(data, enc_hook=encoder))
    data_vals = [
        f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]" for k, v in data_dict.items()
    ]

    CONSOLE.print(Panel.fit("\n".join(data_vals), title=title))


def get_id(ids: list[Id], source: InformationSource) -> str | None:
    return next((x.value for x in ids if x.source is source), None)


def sanitize(value: str | int | None, seperator: Literal["-", "_", ".", " "]) -> str | None:
    if value is None:
        return value
    value = str(value)
    value = re.sub(r"[^0-9a-zA-Z&! ]+", "", value.replace(seperator, " "))
    value = " ".join(value.split())
    return value.replace(" ", seperator)
