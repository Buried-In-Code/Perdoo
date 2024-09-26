__all__ = [
    "Comicvine",
    "LeagueofComicGeeks",
    "Marvel",
    "Metron",
    "OutputFormat",
    "Output",
    "Service",
    "Settings",
    "SyncOption",
]

from enum import Enum
from importlib.util import find_spec
from pathlib import Path
from typing import Any, ClassVar

import tomli_w as tomlwriter
from pydantic import BaseModel, field_validator
from rich.panel import Panel

from perdoo import get_config_root, get_data_root
from perdoo.console import CONSOLE
from perdoo.utils import flatten_dict, values_as_str

try:
    import tomllib as tomlreader  # Python >= 3.11
except ModuleNotFoundError:
    import tomli as tomlreader  # Python < 3.11


class SettingsModel(
    BaseModel,
    populate_by_name=True,
    str_strip_whitespace=True,
    validate_assignment=True,
    extra="ignore",
):
    pass


class SyncOption(Enum):
    FORCE = "Force"
    OUTDATED = "Outdated"
    SKIP = "Skip"

    @staticmethod
    def load(value: str) -> "SyncOption":
        for entry in SyncOption:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid SyncOption")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Flags(SettingsModel):
    convert: bool = True
    sync: SyncOption = SyncOption.OUTDATED
    rename: bool = True
    organize: bool = True
    import_folder: Path | None = None


class Comicvine(SettingsModel):
    api_key: str | None = None


class LeagueofComicGeeks(SettingsModel):
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None


class Marvel(SettingsModel):
    public_key: str | None = None
    private_key: str | None = None


class Metron(SettingsModel):
    password: str | None = None
    username: str | None = None


class OutputFormat(Enum):
    CB7 = "cb7"
    CBT = "cbt"
    CBZ = "cbz"

    @staticmethod
    def load(value: str) -> "OutputFormat":
        for entry in OutputFormat:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid OutputFormat")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Service(Enum):
    COMICVINE = "Comicvine"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"
    MARVEL = "Marvel"
    METRON = "Metron"

    @staticmethod
    def load(value: str) -> "Service":
        for entry in Service:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid Service")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Output(SettingsModel):
    create_comic_info: bool = True
    create_metron_info: bool = True
    format: OutputFormat = OutputFormat.CBZ

    @field_validator("format", mode="before")
    def validate_format(cls, v: str) -> str:
        if v != "cb7":
            return v
        if find_spec("py7zr") is not None:
            return v
        raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")


class Settings(SettingsModel):
    _file: ClassVar[Path] = get_config_root() / "settings.toml"

    collection_folder: Path = get_data_root()
    flags: Flags = Flags()
    comicvine: Comicvine = Comicvine()
    league_of_comic_geeks: LeagueofComicGeeks = LeagueofComicGeeks()
    marvel: Marvel = Marvel()
    metron: Metron = Metron()
    service_order: list[Service] = [
        Service.METRON,
        Service.MARVEL,
        Service.COMICVINE,
        Service.LEAGUE_OF_COMIC_GEEKS,
    ]
    output: Output = Output()

    @classmethod
    def load(cls) -> "Settings":
        if not cls._file.exists():
            cls().save()
        with cls._file.open("rb") as stream:
            content = tomlreader.load(stream)
        return cls(**content)

    def save(self) -> None:
        with self._file.open("wb") as stream:
            content = self.model_dump(by_alias=False, exclude_defaults=True)
            content = values_as_str(content=content)
            tomlwriter.dump(content, stream)

    def update(self, key: str, value: Any) -> None:  # noqa: ANN401
        keys = key.split(".")
        target = self
        for entry in keys[:-1]:
            target = getattr(target, entry)
        setattr(target, keys[-1], value)

    @classmethod
    def display(cls, extras: dict[str, bool | SyncOption | Path] | None = None) -> None:
        if extras is None:
            extras = {}
        default = flatten_dict(content=cls().model_dump())
        file_overrides = flatten_dict(content=cls.load().model_dump())
        default_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            if file_overrides[k] == v
            else f"[dim][repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/][/]"
            for k, v in default.items()
        ]
        override_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            if k not in extras or extras[k] == v
            else f"[dim][repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/][/]"
            for k, v in file_overrides.items()
            if default[k] != v
        ]
        extra_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            for k, v in extras.items()
            if default[k] != v and file_overrides[k] != v
        ]

        CONSOLE.print(Panel.fit("\n".join(default_vals), title="Default"))
        if override_vals:
            CONSOLE.print(Panel.fit("\n".join(override_vals), title=str(cls._file)))
        if extra_vals:
            CONSOLE.print(Panel.fit("\n".join(extra_vals), title="Extras"))
