__all__ = ["Settings"]

from enum import StrEnum
from pathlib import Path
from typing import Annotated, ClassVar, Literal, Self, get_args

from msgspec import Meta, Struct, ValidationError, convert, field, structs, to_builtins
from msgspec.toml import decode, encode
from rich.panel import Panel

from perdoo import get_config_home, get_data_home
from perdoo.console import CONSOLE
from perdoo.formats import ArchiveFormat, ImageFormat
from perdoo.utils import flatten_dict


class ComicInfo(Struct, rename="kebab"):
    create: bool = True
    handle_pages: bool = True


class MetronInfo(Struct, rename="kebab"):
    create: bool = True


class Naming(Struct, rename="kebab"):
    pattern: str = "{publisher-name}/{series-name}[-v{volume}]/{series-name}[-v{volume}][_{format-short}]_#{number:3}"  # noqa: E501
    seperator: Literal["-", "_", ".", " "] = "-"


class Output(Struct, rename="kebab"):
    archive_format: ArchiveFormat = ArchiveFormat.CBZ
    comic_info: ComicInfo = field(default_factory=ComicInfo)
    folder: Path = field(default_factory=lambda: get_data_home() / "comics")
    image_format: ImageFormat | None = None
    metron_info: MetronInfo = field(default_factory=MetronInfo)
    naming: Naming = field(default_factory=Naming)


class Comicvine(Struct, rename="kebab"):
    api_key: str | None = None


class Metron(Struct, rename="kebab"):
    token: str | None = None


class Service(StrEnum):
    COMICVINE = "Comicvine"
    METRON = "Metron"

    def __str__(self) -> str:
        return self.value


class Services(Struct, rename="kebab"):
    comicvine: Comicvine = field(default_factory=Comicvine)
    metron: Metron = field(default_factory=Metron)
    order: list[Service] = field(default_factory=lambda: [Service.METRON, Service.COMICVINE])


class Sync(Struct, rename="kebab"):
    cover_hash_distance: Annotated[
        int, Meta(ge=0, le=64, description="'cover-hash-distance' must be between 0 and 64")
    ] = 10
    days: Annotated[int, Meta(ge=7, description="'days' must be greater than 6")] = 28


class Settings(Struct, rename="kebab"):
    _file: ClassVar[Path] = get_config_home() / "settings.toml"

    output: Output = field(default_factory=Output)
    removals: list[str] = field(
        default_factory=lambda: ["*.db", "*.ini", "*.nfo", "*.sfv", ".DS_Store"]
    )
    services: Services = field(default_factory=Services)
    sync: Sync = field(default_factory=Sync)

    @property
    def path(self) -> Path:
        return self._file

    @classmethod
    def load(cls) -> "Settings":
        if not cls._file.exists():
            return cls().save()
        try:
            return convert(
                _restore_none(value=decode(cls._file.read_bytes()), struct_type=cls),
                type=cls,
                dec_hook=lambda typ, obj: (
                    Path(obj) if typ is Path and isinstance(obj, str) else obj
                ),
            )
        except ValidationError as err:
            raise ValueError(f"Invalid settings file {cls._file}: {err}") from err

    def save(self) -> Self:
        def encoder(obj: object) -> object:
            return str(obj) if isinstance(obj, Path) else obj

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(encode(_toml_serializable(value=to_builtins(self, enc_hook=encoder))))
        return self

    @classmethod
    def display(cls) -> None:
        def encoder(obj: object) -> object:
            return str(obj) if isinstance(obj, Path) else obj

        default = flatten_dict(content=to_builtins(cls(), enc_hook=encoder))
        override = flatten_dict(content=to_builtins(cls.load(), enc_hook=encoder))
        default_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            if k in override and override[k] == v
            else f"[dim][repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/][/]"
            for k, v in default.items()
        ]
        override_vals = [
            f"[repr.attrib_name]{k}[/]: [repr.attrib_value]{v}[/]"
            for k, v in override.items()
            if k not in default or default[k] != v
        ]

        CONSOLE.print(Panel.fit("\n".join(default_vals), title="Default Settings"))
        CONSOLE.print(Panel.fit("\n".join(override_vals), title=str(cls._file)))


def _toml_serializable(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, dict):
        return {key: _toml_serializable(value=item) for key, item in value.items()}
    if isinstance(value, list):
        return [_toml_serializable(value=item) for item in value]
    return value


def _restore_none(value: object, struct_type: type[Struct]) -> object:
    if not isinstance(value, dict):
        return value
    for info in structs.fields(struct_type):
        item = value.get(info.encode_name)
        if item == "" and type(None) in get_args(info.type):
            value[info.encode_name] = None
        elif (
            isinstance(item, dict) and isinstance(info.type, type) and issubclass(info.type, Struct)
        ):
            _restore_none(value=item, struct_type=info.type)
    return value
