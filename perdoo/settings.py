__all__ = ["Settings"]

from enum import Enum
from pathlib import Path
from typing import ClassVar, Literal

from msgspec import Struct, ValidationError, field, to_builtins
from msgspec.toml import decode, encode
from rich.panel import Panel

from perdoo import get_config_home, get_data_home
from perdoo.console import CONSOLE
from perdoo.utils import flatten_dict

try:
    from typing import Self  # Python >= 3.11  # ty:ignore[unresolved-import]
except ImportError:
    from typing_extensions import Self  # Python < 3.11


class ComicInfo(Struct, rename="kebab"):
    create: bool = True
    handle_pages: bool = True


class MetronInfo(Struct, rename="kebab"):
    create: bool = True


class Naming(Struct, rename="kebab"):
    seperator: Literal["-", "_", ".", " "] = "-"
    default: str = "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_#{number:3}"
    annual: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Annual_#{number:2}"
    )
    digital_chapter: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_Chapter_#{number:3}"
    )
    graphic_novel: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_GN_#{number:2}"
    )
    hardcover: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_HC_#{number:2}"
    )
    limited_series: str | None = None
    omnibus: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_OB_#{number:2}"
    )
    one_shot: str | None = None
    single_issue: str | None = None
    trade_paperback: str | None = (
        "{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_TPB_#{number:2}"
    )

    def pattern_for(self, format_: str | None) -> str:
        overrides = {
            "Annual": self.annual,
            "Digitial Chapter": self.digital_chapter,
            "Graphic Novel": self.graphic_novel,
            "Hardcover": self.hardcover,
            "Limited Series": self.limited_series,
            "Omnibus": self.omnibus,
            "One-Shot": self.one_shot,
            "Single Issue": self.single_issue,
            "Trade Paperback": self.trade_paperback,
        }
        return overrides.get(format_ or "") or self.default


class Output(Struct, rename="kebab"):
    comic_info: ComicInfo = field(default_factory=ComicInfo)
    folder: Path = get_data_home() / "comics"
    format: Literal["cbz", "cbt", "cb7"] = "cbz"
    image_extensions: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".jxl")
    metron_info: MetronInfo = field(default_factory=MetronInfo)
    naming: Naming = field(default_factory=Naming)


class Comicvine(Struct, rename="kebab"):
    api_key: str | None = None


class Metron(Struct, rename="kebab"):
    token: str | None = None


class Service(str, Enum):
    COMICVINE = "Comicvine"
    METRON = "Metron"

    def __str__(self) -> str:
        return self.value


class Services(Struct, rename="kebab"):
    comicvine: Comicvine = field(default_factory=Comicvine)
    metron: Metron = field(default_factory=Metron)
    order: tuple[Service, ...] = (Service.METRON, Service.COMICVINE)


class Settings(Struct, rename="kebab"):
    _file: ClassVar[Path] = get_config_home() / "settings.toml"

    output: Output = field(default_factory=Output)
    services: Services = field(default_factory=Services)

    @property
    def path(self) -> Path:
        return self._file

    @classmethod
    def load(cls) -> "Settings":
        if not cls._file.exists():
            return cls().save()
        try:
            return decode(
                cls._file.read_bytes(),
                type=cls,
                dec_hook=lambda typ, obj: (
                    Path(obj) if typ is Path and isinstance(obj, str) else obj
                ),
            )
        except ValidationError as err:
            raise ValueError(f"Invalid settings file {cls._file}: {err}") from err

    def save(self) -> Self:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_bytes(
            encode(
                self,
                enc_hook=lambda obj: (
                    str(obj) if isinstance(obj, Path) else "" if obj is None else obj
                ),
            )
        )
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
