__all__ = ["Identifications", "Details", "list_files", "sanitize", "flatten_dict"]

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from natsort import humansorted, ns

LOGGER = logging.getLogger(__name__)


@dataclass
class Identifications:
    search: str | None = None
    comicvine: int | None = None
    league: int | None = None
    marvel: int | None = None
    metron: int | None = None


@dataclass
class Details:
    series: Identifications | None
    issue: Identifications | None


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
        else:
            items[new_key] = value
    return items
