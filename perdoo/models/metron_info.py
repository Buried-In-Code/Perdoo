__all__ = [
    "GTIN",
    "AgeRating",
    "AlternativeName",
    "Arc",
    "Credit",
    "Format",
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
from typing import Generic, TypeVar

from pydantic import HttpUrl, PositiveInt
from pydantic_xml import attr, computed_attr, element, wrapped

from perdoo.models._base import PascalModel
from perdoo.utils import sanitize

T = TypeVar("T")


class InformationSource(Enum):
    ANILIST = "AniList"
    COMIC_VINE = "Comic Vine"
    GRAND_COMICS_DATABASE = "Grand Comics Database"
    MARVEL = "Marvel"
    METRON = "Metron"
    MYANIMELIST = "MyAnimeList"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"

    @staticmethod
    def load(value: str) -> "InformationSource":
        for entry in InformationSource:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isn't a valid InformationSource")

    def __str__(self) -> str:
        return self.value


class Source(PascalModel):
    source: InformationSource = attr(name="source")
    value: PositiveInt

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
    alternatives: list[T] = wrapped(
        path="Alternatives", entity=element(tag="Alternative", default_factory=list)
    )
    primary: T = element()


class Resource(PascalModel, Generic[T]):
    value: T
    id: PositiveInt | None = attr(name="id", default=None)

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
    id: PositiveInt | None = attr(name="id", default=None)
    imprint: Resource[str] | None = element(default=None)
    name: str = element()


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
        raise ValueError(f"'{value}' isn't a valid Format")

    def __str__(self) -> str:
        return self.value


class AlternativeName(Resource[str]):
    lang: str = attr(name="lang", default="en")


class Series(PascalModel):
    alternative_names: list[AlternativeName] = wrapped(
        path="AlternativeNames", entity=element(tag="AlternativeName", default_factory=list)
    )
    format: Format | None = element(default=None)
    id: PositiveInt | None = attr(name="id", default=None)
    lang: str = attr(name="lang", default="en")
    name: str = element()
    sort_name: str | None = element(default=None)
    volume: int | None = element(default=None)
    start_year: int | None = element(default=None)

    @property
    def filename(self) -> str:
        return sanitize(
            self.name if not self.volume or self.volume == 1 else f"{self.name} v{self.volume}"
        )


class Price(PascalModel):
    country: str = attr(name="country")
    value: Decimal

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


class Arc(PascalModel):
    id: PositiveInt | None = attr(name="id", default=None)
    name: str = element()
    number: PositiveInt | None = element(default=None)

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
    designation: str | None = element(default=None)
    id: PositiveInt | None = attr(name="id", default=None)
    name: str = element()

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
    isbn: str | None = element(tag="ISBN", default=None)
    upc: str | None = element(tag="UPC", default=None)


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
        raise ValueError(f"'{value}' isn't a valid AgeRating")

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
        raise ValueError(f"'{value}' isn't a valid Role")

    def __str__(self) -> str:
        return self.value


class Credit(PascalModel):
    creator: Resource[str] = element()
    roles: list[Resource[Role]] = wrapped(
        path="Roles", entity=element(tag="Role", default_factory=list)
    )

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


class MetronInfo(PascalModel):
    age_rating: AgeRating = element(default=AgeRating.UNKNOWN)
    arcs: list[Arc] = wrapped(path="Arcs", entity=element(tag="Arc", default_factory=list))
    characters: list[Resource[str]] = wrapped(
        path="Characters", entity=element(tag="Character", default_factory=list)
    )
    collection_title: str | None = element(default=None)
    cover_date: date | None = element(default=None)
    credits: list[Credit] = wrapped(
        path="Credits", entity=element(tag="Credit", default_factory=list)
    )
    genres: list[Resource[str]] = wrapped(
        path="Genres", entity=element(tag="Genre", default_factory=list)
    )
    gtin: GTIN | None = element(tag="GTIN", default=None)
    id: InformationList[Source] | None = element(tag="ID", default=None)
    last_modified: datetime | None = element(default=None)
    locations: list[Resource[str]] = wrapped(
        path="Locations", entity=element(tag="Location", default_factory=list)
    )
    notes: str | None = element(default=None)
    number: str | None = element(default=None)
    page_count: int = element(default=0)
    prices: list[Price] = wrapped(path="Prices", entity=element(tag="Price", default_factory=list))
    publisher: Publisher | None = element(default=None)
    reprints: list[Resource[str]] = wrapped(
        path="Reprints", entity=element(tag="Reprint", default_factory=list)
    )
    series: Series = element()
    store_date: date | None = element(default=None)
    stories: list[Resource[str]] = wrapped(
        path="Stories", entity=element(tag="Story", default_factory=list)
    )
    summary: str | None = element(default=None)
    tags: list[Resource[str]] = wrapped(
        path="Tags", entity=element(tag="Tag", default_factory=list)
    )
    teams: list[Resource[str]] = wrapped(
        path="Teams", entity=element(tag="Team", default_factory=list)
    )
    universes: list[Universe] = wrapped(
        path="Universes", entity=element(tag="Universe", default_factory=list)
    )
    urls: InformationList[HttpUrl] | None = element(tag="URLs", default=None)
    volume: str | None = element(default=None)

    @computed_attr(ns="xsi", name="noNamespaceSchemaLocation")
    def schema_location(self) -> str:
        return "https://raw.githubusercontent.com/Metron-Project/metroninfo/master/drafts/v1.0/MetronInfo.xsd"

    @property
    def filename(self) -> str:
        identifier = ""
        if self.number:
            padded_number = self.number.zfill(
                {Format.SINGLE_ISSUE: 3, Format.DIGITAL_CHAPTER: 3}.get(self.series.format, 2)
            )
            identifier = f"_#{padded_number}"
        elif self.collection_title:
            identifier = f"_{sanitize(self.collection_title)}"

        return {
            Format.ANNUAL: f"{self.series.filename}_Annual{identifier}",
            Format.DIGITAL_CHAPTER: f"{self.series.filename}_Chapter{identifier}",
            Format.GRAPHIC_NOVEL: f"{self.series.filename}{identifier}_GN",
            Format.HARDCOVER: f"{self.series.filename}{identifier}_HC",
            Format.OMNIBUS: f"{self.series.filename}{identifier}",
            Format.TRADE_PAPERBACK: f"{self.series.filename}{identifier}_TPB",
        }.get(self.series.format, f"{self.series.filename}{identifier}")
