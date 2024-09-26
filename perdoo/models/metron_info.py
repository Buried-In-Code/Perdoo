__all__ = [
    "GTIN",
    "AgeRating",
    "AlternativeName",
    "Arc",
    "Credit",
    "Format",
    "Genre",
    "InformationList",
    "InformationSource",
    "MetronInfo",
    "Price",
    "Publisher",
    "Resource",
    "Role",
    "Series",
    "Source",
    "Universe",
]

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import ClassVar, Generic, TypeVar

import xmltodict
from pydantic import Field, HttpUrl, PositiveInt

from perdoo.models._base import InfoModel, PascalModel
from perdoo.utils import sanitize, values_as_str

T = TypeVar("T")


class InformationSource(Enum):
    COMIC_VINE = "Comic Vine"
    GRAND_COMICS_DATABASE = "Grand Comics Database"
    MARVEL = "Marvel"
    METRON = "Metron"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"

    @staticmethod
    def load(value: str) -> "InformationSource":
        for entry in InformationSource:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.InformationSource")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Source(PascalModel):
    value: PositiveInt = Field(alias="#text")
    source: InformationSource = Field(alias="@source")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.source < other.source

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.source == other.source

    def __hash__(self) -> int:
        return hash((type(self), self.source))


class InformationList(PascalModel, Generic[T]):
    primary: T
    alternatives: list[T] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {"Alternatives": "Alternative"}


class Resource(PascalModel, Generic[T]):
    value: T = Field(alias="#text")
    id: PositiveInt | None = Field(alias="@id", default=None)

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value == other.value

    def __hash__(self) -> int:
        return hash((type(self), self.value))


class Publisher(PascalModel):
    name: str
    imprint: Resource | None = None
    id: PositiveInt | None = Field(alias="@id", default=None)


class Format(Enum):
    ANNUAL = "Annual"
    DIGITAL_CHAPTER = "Digital Chapter"
    GRAPHIC_NOVEL = "Graphic Novel"
    HARDCOVER = "Hardcover"
    LIMITED_SERIES = "Limited Series"
    OMNIBUS = "Omnibus"
    ONE_SHOT = "One-Shot"
    SINGLE_ISSUE = "Single Issue"
    TRADE_PAPERBACK = "Trade Paperback"

    @staticmethod
    def load(value: str) -> "Format":
        for entry in Format:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.Format")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class AlternativeName(Resource[str]):
    lang: str = Field(alias="@lang", default="en")


class Series(PascalModel):
    lang: str = Field(alias="@lang", default="en")
    id: PositiveInt | None = Field(alias="@id", default=None)
    name: str
    sort_name: str | None = None
    volume: int | None = None
    format: Format | None = None
    start_year: int | None = None
    alternative_names: list[AlternativeName] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {"AlternativeNames": "AlternativeName"}

    @property
    def filename(self) -> str:
        return sanitize(self.name if self.volume == 1 else f"{self.name} v{self.volume}")


class Price(PascalModel):
    value: Decimal = Field(alias="#text")
    country: str = Field(alias="@country")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.country < other.country

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.country == other.country

    def __hash__(self) -> int:
        return hash((type(self), self.country))


class Genre(Enum):
    ADULT = "Adult"
    CRIME = "Crime"
    ESPIONAGE = "Espionage"
    FANTASY = "Fantasy"
    HISTORICAL = "Historical"
    HORROR = "Horror"
    HUMOR = "Humor"
    MANGA = "Manga"
    PARODY = "Parody"
    ROMANCE = "Romance"
    SCIENCE_FICTION = "Science Fiction"
    SPORT = "Sport"
    SUPER_HERO = "Super-Hero"
    WAR = "War"
    WESTERN = "Western"

    @staticmethod
    def load(value: str) -> "Genre":
        for entry in Genre:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.Genre")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Arc(PascalModel):
    name: str
    number: PositiveInt | None = None
    id: PositiveInt | None = Field(alias="@id", default=None)

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name < other.name

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash((type(self), self.name))


class Universe(PascalModel):
    name: str
    designation: str | None = None
    id: PositiveInt | None = Field(alias="@id", default=None)

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name < other.name

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash((type(self), self.name))


class GTIN(PascalModel):
    isbn: str | None = Field(alias="ISBN", default=None)
    upc: str | None = Field(alias="UPC", default=None)


class AgeRating(Enum):
    UNKNOWN = "Unknown"
    EVERYONE = "Everyone"
    TEEN = "Teen"
    TEEN_PLUS = "Teen Plus"
    MATURE = "Mature"

    @staticmethod
    def load(value: str) -> "AgeRating":
        for entry in AgeRating:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.AgeRating")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Role(Enum):
    WRITER = "Writer"
    SCRIPT = "Script"
    STORY = "Story"
    PLOT = "Plot"
    INTERVIEWER = "Interviewer"
    ARTIST = "Artist"
    PENCILLER = "Penciller"
    BREAKDOWNS = "Breakdowns"
    ILLUSTRATOR = "Illustrator"
    LAYOUTS = "Layouts"
    INKER = "Inker"
    EMBELLISHER = "Embellisher"
    FINISHES = "Finishes"
    INK_ASSISTS = "Ink Assists"
    COLORIST = "Colorist"
    COLOR_SEPARATIONS = "Color Separations"
    COLOR_ASSISTS = "Color Assists"
    COLOR_FLATS = "Color Flats"
    DIGITAL_ART_TECHNICIAN = "Digital Art Technician"
    GRAY_TONE = "Gray Tone"
    LETTERER = "Letterer"
    COVER = "Cover"
    EDITOR = "Editor"
    CONSULTING_EDITOR = "Consulting Editor"
    ASSISTANT_EDITOR = "Assistant Editor"
    ASSOCIATE_EDITOR = "Associate Editor"
    GROUP_EDITOR = "Group Editor"
    SENIOR_EDITOR = "Senior Editor"
    MANAGING_EDITOR = "Managing Editor"
    COLLECTION_EDITOR = "Collection Editor"
    PRODUCTION = "Production"
    DESIGNER = "Designer"
    LOGO_DESIGN = "Logo Design"
    TRANSLATOR = "Translator"
    SUPERVISING_EDITOR = "Supervising Editor"
    EXECUTIVE_EDITOR = "Executive Editor"
    EDITOR_IN_CHIEF = "Editor In Chief"
    PRESIDENT = "President"
    PUBLISHER = "Publisher"
    CHIEF_CREATIVE_OFFICER = "Chief Creative Officer"
    EXECUTIVE_PRODUCER = "Executive Producer"
    OTHER = "Other"

    @staticmethod
    def load(value: str) -> "Role":
        for entry in Role:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.Role")

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self) -> str:
        return self.value


class Credit(PascalModel):
    creator: Resource[str]
    roles: list[Resource[Role]] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {"Roles": "Role"}

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.creator < other.creator

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.creator == other.creator

    def __hash__(self) -> int:
        return hash((type(self), self.creator))


class MetronInfo(PascalModel, InfoModel):
    id: InformationList[Source] | None = Field(alias="ID", default=None)
    publisher: Publisher
    series: Series
    collection_title: str | None = None
    number: str | None = None
    stories: list[Resource[str]] = Field(default_factory=list)
    summary: str | None = None
    prices: list[Price] = Field(default_factory=list)
    cover_date: date | None = None
    store_date: date | None = None
    page_count: int = 0
    notes: str | None = None
    genres: list[Resource[Genre]] = Field(default_factory=list)
    tags: list[Resource[str]] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)
    characters: list[Resource[str]] = Field(default_factory=list)
    teams: list[Resource[str]] = Field(default_factory=list)
    universes: list[Universe] = Field(default_factory=list)
    locations: list[Resource[str]] = Field(default_factory=list)
    reprints: list[Resource[str]] = Field(default_factory=list)
    gtin: GTIN | None = Field(alias="GTIN", default=None)
    age_rating: AgeRating = Field(default=AgeRating.UNKNOWN)
    urls: InformationList[HttpUrl] | None = Field(alias="URLs", default=None)
    credits: list[Credit] = Field(default_factory=list)
    last_modified: datetime | None = None

    list_fields: ClassVar[dict[str, str]] = {
        **Credit.list_fields,
        **InformationList.list_fields,
        **Series.list_fields,
        "Arcs": "Arc",
        "Characters": "Character",
        "Credits": "Credit",
        "Genres": "Genre",
        "Locations": "Location",
        "Prices": "Price",
        "Reprints": "Reprint",
        "Stories": "Story",
        "Tags": "Tag",
        "Teams": "Team",
        "Universes": "Universe",
    }
    text_fields: ClassVar[list[str]] = [
        "Characters",
        "Creator",
        "Genres",
        "Locations",
        "Prices",
        "Reprints",
        "Roles",
        "Stories",
        "Tags",
        "Teams",
    ]

    def get_file(self, root: Path, extension: str) -> Path:
        identifier = ""
        if self.number:
            padded_number = self.number.zfill(
                {Format.SINGLE_ISSUE: 3, Format.DIGITAL_CHAPTER: 3}.get(self.series.format, 2)
            )
            identifier = f"_#{padded_number}"
        elif self.collection_title:
            identifier = f"_{sanitize(self.collection_title)}"

        filename = {
            Format.ANNUAL: f"{self.series.filename}_Annual{identifier}",
            Format.DIGITAL_CHAPTER: f"{self.series.filename}_Chapter{identifier}",
            Format.GRAPHIC_NOVEL: f"{self.series.filename}{identifier}_GN",
            Format.HARDCOVER: f"{self.series.filename}{identifier}_HC",
            Format.OMNIBUS: f"{self.series.filename}{identifier}",
            Format.TRADE_PAPERBACK: f"{self.series.filename}{identifier}_TPB",
        }.get(self.series.format, f"{self.series.filename}{identifier}")

        return (
            root / sanitize(self.publisher.name) / self.series.filename / f"{filename}.{extension}"
        )

    @classmethod
    def from_bytes(cls, content: bytes) -> "MetronInfo":
        xml_content = xmltodict.parse(content, force_list=list(cls.list_fields.values()))
        return cls(**xml_content["MetronInfo"])

    def to_file(self, file: Path) -> None:
        content = self.model_dump(by_alias=True, exclude_none=True)
        self.wrap_list(mappings=self.list_fields, content=content)
        content = values_as_str(content=content)
        content["@xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
        content["@xsi:noNamespaceSchemaLocation"] = (
            "https://raw.githubusercontent.com/Metron-Project/metroninfo/master/drafts/v1.0/MetronInfo.xsd"
        )

        with file.open("wb") as stream:
            xmltodict.unparse(
                {"MetronInfo": {k: content[k] for k in sorted(content)}},
                output=stream,
                short_empty_elements=True,
                pretty=True,
                indent=" " * 2,
            )
