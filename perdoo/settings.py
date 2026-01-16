__all__ = [
    "ComicInfo",
    "Comicvine",
    "Metron",
    "MetronInfo",
    "Naming",
    "Output",
    "Service",
    "Services",
    "Settings",
]

from enum import Enum
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal

import tomli_w as tomlwriter
from pydantic import BeforeValidator
from rich.panel import Panel

from perdoo import get_config_root, get_data_root
from perdoo.console import CONSOLE
from perdoo.utils import BaseModel, blank_is_none, flatten_dict

try:
    from typing import Self  # Python >= 3.11
except ImportError:
    from typing_extensions import Self  # Python < 3.11

try:
    import tomllib as tomlreader  # Python >= 3.11
except ModuleNotFoundError:
    import tomli as tomlreader  # Python < 3.11


class SettingsModel(BaseModel, extra="ignore"): ...


class ComicInfo(SettingsModel):
    create: bool = True
    handle_pages: bool = True


class MetronInfo(SettingsModel):
    create: bool = True


class Naming(SettingsModel):
    seperator: Literal["-", "_", ".", " "] = "-"
    default: str = "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_#{number:3}"
    annual: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Annual_#{number:2}"
    )
    digital_chapter: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Chapter_#{number:3}"
    )
    graphic_novel: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_GN_#{number:2}"
    )
    hardcover: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_HC_#{number:2}"
    )
    limited_series: Annotated[str | None, BeforeValidator(blank_is_none)] = None
    omnibus: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_OB_#{number:2}"
    )
    one_shot: Annotated[str | None, BeforeValidator(blank_is_none)] = None
    single_issue: Annotated[str | None, BeforeValidator(blank_is_none)] = None
    trade_paperback: Annotated[str | None, BeforeValidator(blank_is_none)] = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_TPB_#{number:2}"
    )


class Output(SettingsModel):
    comic_info: ComicInfo = ComicInfo()
    folder: Path = get_data_root()
    metron_info: MetronInfo = MetronInfo()
    naming: Naming = Naming()


class Comicvine(SettingsModel):
    api_key: Annotated[str | None, BeforeValidator(blank_is_none)] = None


class Metron(SettingsModel):
    password: Annotated[str | None, BeforeValidator(blank_is_none)] = None
    username: Annotated[str | None, BeforeValidator(blank_is_none)] = None


class Service(str, Enum):
    COMICVINE = "Comicvine"
    METRON = "Metron"

    def __str__(self) -> str:
        return self.value


class Services(SettingsModel):
    comicvine: Comicvine = Comicvine()
    metron: Metron = Metron()
    order: tuple[Service, ...] = (Service.METRON, Service.COMICVINE)


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

    output: Output = Output()
    services: Services = Services()

    @property
    def path(self) -> Path:
        return self._file

    @classmethod
    def load(cls) -> Self:
        if not cls._file.exists():
            cls().save()
        with cls._file.open("rb") as stream:
            content = tomlreader.load(stream)
        return cls(**content)

    def save(self) -> Self:
        with self.path.open("wb") as stream:
            content = self.model_dump(by_alias=False)
            content = _stringify_values(content=content)
            tomlwriter.dump(content, stream)
        return self

    @classmethod
    def display(cls) -> None:
        default = flatten_dict(content=cls().model_dump())
        file_overrides = flatten_dict(content=cls.load().model_dump())
        default_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            if k in file_overrides and file_overrides[k] == v
            else f"[dim][repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/][/]"
            for k, v in default.items()
        ]
        override_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            for k, v in file_overrides.items()
            if k not in default or default[k] != v
        ]

        CONSOLE.print(Panel.fit("\n".join(default_vals), title="Default"))
        CONSOLE.print(Panel.fit("\n".join(override_vals), title=str(cls._file)))
