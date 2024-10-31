__all__ = [
    "ComicInfo",
    "MetronInfo",
    "Metadata",
    "Output",
    "Comicvine",
    "LeagueOfComicGeeks",
    "Marvel",
    "Metron",
    "Service",
    "Services",
    "Settings",
]

from enum import Enum
from importlib.util import find_spec
from pathlib import Path
from typing import Any, ClassVar, Literal

import tomli_w as tomlwriter
from pydantic import BaseModel, field_validator
from rich.panel import Panel

from perdoo import get_config_root, get_data_root
from perdoo.console import CONSOLE
from perdoo.utils import flatten_dict

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


class ComicInfo(SettingsModel):
    create: bool = True
    handle_pages: bool = True


class MetronInfo(SettingsModel):
    create: bool = True


class Metadata(SettingsModel):
    comic_info: ComicInfo = ComicInfo()
    metron_info: MetronInfo = MetronInfo()


class Output(SettingsModel):
    folder: Path = get_data_root()
    format: Literal["cb7", "cbt", "cbz"] = "cbz"
    metadata: Metadata = Metadata()

    @field_validator("format", mode="before")
    def validate_format(cls, value: str) -> str:
        if value == "cb7" and find_spec("py7zr") is None:
            raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")
        return value


class Comicvine(SettingsModel):
    api_key: str | None = None


class LeagueOfComicGeeks(SettingsModel):
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None


class Marvel(SettingsModel):
    public_key: str | None = None
    private_key: str | None = None


class Metron(SettingsModel):
    password: str | None = None
    username: str | None = None


class Service(Enum):
    COMICVINE = "Comicvine"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"
    MARVEL = "Marvel"
    METRON = "Metron"

    @staticmethod
    def load(value: str) -> "Service":
        for entry in Service:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isn't a valid Service")

    def __str__(self) -> str:
        return self.value


class Services(SettingsModel):
    comicvine: Comicvine = Comicvine()
    league_of_comic_geeks: LeagueOfComicGeeks = LeagueOfComicGeeks()
    marvel: Marvel = Marvel()
    metron: Metron = Metron()
    order: tuple[Service, ...] = (Service.METRON, Service.MARVEL, Service.COMICVINE)


def _stringify_values(content: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for key, value in content.items():
        if isinstance(value, bool):
            value = str(value)
        if not value:
            continue
        if isinstance(value, dict):
            value = _stringify_values(content=value)
        elif isinstance(value, list | tuple | set):
            value = [_stringify_values(content=x) if isinstance(x, dict) else str(x) for x in value]
        else:
            value = str(value)
        output[key] = value
    return output


class Settings(SettingsModel):
    _file: ClassVar[Path] = get_config_root() / "settings.toml"

    image_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp", ".jxl")
    output: Output = Output()
    services: Services = Services()

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
            content = _stringify_values(content=content)
            tomlwriter.dump(content, stream)

    def update(self, key: str, value: Any) -> None:  # noqa: ANN401
        keys = key.split(".")
        target = self
        for entry in keys[:-1]:
            target = getattr(target, entry)
        setattr(target, keys[-1], value)

    @classmethod
    def display(cls, extras: dict[str, Any] | None = None) -> None:
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
            for k, v in file_overrides.items()
            if default[k] != v
        ]
        extra_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]" for k, v in extras.items()
        ]

        CONSOLE.print(Panel.fit("\n".join(default_vals), title="Default"))
        if override_vals:
            CONSOLE.print(Panel.fit("\n".join(override_vals), title=str(cls._file)))
        if extra_vals:
            CONSOLE.print(Panel.fit("\n".join(extra_vals), title="Extras"))
