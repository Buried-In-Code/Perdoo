from __future__ import annotations

__all__ = [
    "Comicvine",
    "LeagueofComicGeeks",
    "Marvel",
    "Metron",
    "OutputFormat",
    "Output",
    "Settings",
]

from enum import Enum
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar

import tomli_w as tomlwriter
from pydantic import BaseModel, field_validator

from perdoo import get_config_dir, get_input_dir

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


class Comicvine(SettingsModel):
    api_key: str = ""


class LeagueofComicGeeks(SettingsModel):
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""


class Marvel(SettingsModel):
    public_key: str = ""
    private_key: str = ""


class Metron(SettingsModel):
    password: str = ""
    username: str = ""


class OutputFormat(Enum):
    CB7 = "cb7"
    CBT = "cbt"
    CBZ = "cbz"

    @staticmethod
    def load(value: str) -> OutputFormat:
        for entry in OutputFormat:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid OutputFormat")

    def __lt__(self: OutputFormat, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: OutputFormat) -> str:
        return self.value


class Service(Enum):
    COMICVINE = "Comicvine"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"
    MARVEL = "Marvel"
    METRON = "Metron"

    @staticmethod
    def load(value: str) -> Service:
        for entry in Service:
            if entry.value.casefold() == value.casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid Service")

    def __lt__(self: Service, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: Service) -> str:
        return self.value


class Output(SettingsModel):
    create_comic_info: bool = True
    create_metron_info: bool = True
    create_metadata: bool = True
    format: OutputFormat = OutputFormat.CBZ

    @field_validator("format", mode="before")
    def validate_format(cls: type[Output], v: str) -> str:
        if v != "cb7":
            return v
        if find_spec("py7zr") is not None:
            return v
        raise ImportError("Install Perdoo with the cb7 dependency group to use CB7 files.")


class Settings(SettingsModel):
    _filename: ClassVar[Path] = get_config_dir() / "settings.toml"
    input_folder: Path = get_input_dir()
    output_folder: Path = get_input_dir()
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
    def load(cls: type[Settings]) -> Settings:
        if not cls._filename.exists():
            cls().save()
        with cls._filename.open("rb") as stream:
            content = tomlreader.load(stream)
        return cls(**content)

    def save(self: Settings) -> Settings:
        with self._filename.open("wb") as stream:
            content = self.dict(by_alias=False)
            content["input_folder"] = str(content["input_folder"])
            content["output_folder"] = str(content["output_folder"])
            content["service_order"] = [str(x) for x in content["service_order"]]
            content["output"]["format"] = str(content["output"]["format"])
            tomlwriter.dump(content, stream)
        return self
