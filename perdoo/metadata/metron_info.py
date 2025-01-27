__all__ = [
    "GTIN",
    "AgeRating",
    "AlternativeName",
    "Arc",
    "Credit",
    "Format",
    "Id",
    "InformationSource",
    "MetronInfo",
    "Price",
    "Publisher",
    "Resource",
    "Role",
    "Series",
    "Universe",
    "Url",
]

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar

from pydantic import HttpUrl, NonNegativeInt, PositiveInt
from pydantic_xml import attr, computed_attr, element, wrapped

from perdoo.metadata._base import PascalModel
from perdoo.settings import Naming

T = TypeVar("T")


class AgeRating(Enum):
    UNKNOWN = "Unknown"
    EVERYONE = "Everyone"
    TEEN = "Teen"
    TEEN_PLUS = "Teen Plus"
    MATURE = "Mature"
    EXPLICIT = "Explicit"
    ADULT = "Adult"

    @staticmethod
    def load(value: str) -> "AgeRating":
        for entry in AgeRating:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isn't a valid AgeRating")

    def __str__(self) -> str:
        return self.value


class Arc(PascalModel):
    id: str | None = attr(name="id", default=None)
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


class Resource(PascalModel, Generic[T]):
    value: T
    id: str | None = attr(name="id", default=None)

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


class GTIN(PascalModel):
    isbn: str | None = element(tag="ISBN", default=None)
    upc: str | None = element(tag="UPC", default=None)


class InformationSource(Enum):
    ANILIST = "AniList"
    COMIC_VINE = "Comic Vine"
    GRAND_COMICS_DATABASE = "Grand Comics Database"
    KITSU = "Kitsu"
    MANGA_DEX = "MangaDex"
    MANGA_UPDATES = "MangaUpdates"
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


class Id(PascalModel):
    primary: bool = attr(name="primary", default=False)
    source: InformationSource = attr(name="source")
    value: str

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


class Publisher(PascalModel):
    id: str | None = attr(name="id", default=None)
    imprint: Resource[str] | None = element(default=None)
    name: str = element()


class AlternativeName(Resource[str]):
    lang: str = attr(name="lang", default="en")


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


class Series(PascalModel):
    alternative_names: list[AlternativeName] = wrapped(
        path="AlternativeNames", entity=element(tag="AlternativeName", default_factory=list)
    )
    format: Format | None = element(default=None)
    id: str | None = attr(name="id", default=None)
    issue_count: PositiveInt | None = element(default=None)
    lang: str = attr(name="lang", default="en")
    name: str = element()
    sort_name: str | None = element(default=None)
    start_year: int | None = element(default=None)
    volume: NonNegativeInt | None = element(default=None)
    volume_count: PositiveInt | None = element(default=None)


class Universe(PascalModel):
    designation: str | None = element(default=None)
    id: str | None = attr(name="id", default=None)
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


class Url(PascalModel):
    primary: bool = attr(name="primary", default=False)
    value: HttpUrl

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
    ids: list[Id] = wrapped("IDS", entity=element(tag="ID", default_factory=list))
    last_modified: datetime | None = element(default=None)
    locations: list[Resource[str]] = wrapped(
        path="Locations", entity=element(tag="Location", default_factory=list)
    )
    manga_volume: str | None = element(default=None)
    notes: str | None = element(default=None)
    number: str | None = element(default=None)
    page_count: NonNegativeInt = element(default=0)
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
    urls: list[Url] = wrapped(path="URLS", entity=element(tag="URLs", default_factory=list))

    @computed_attr(ns="xsi", name="noNamespaceSchemaLocation")
    def schema_location(self) -> str:
        return "https://raw.githubusercontent.com/Metron-Project/metroninfo/master/schema/v1.0/MetronInfo.xsd"

    def get_filename(self, settings: Naming) -> str:
        return self.evaluate_pattern(
            pattern_map=PATTERN_MAP,
            pattern={
                Format.ANNUAL: settings.annual or settings.default,
                Format.DIGITAL_CHAPTER: settings.digital_chapter or settings.default,
                Format.GRAPHIC_NOVEL: settings.graphic_novel or settings.default,
                Format.HARDCOVER: settings.hardcover or settings.default,
                Format.LIMITED_SERIES: settings.limited_series or settings.default,
                Format.OMNIBUS: settings.omnibus or settings.default,
                Format.ONE_SHOT: settings.one_shot or settings.default,
                Format.SINGLE_ISSUE: settings.single_issue or settings.default,
                Format.TRADE_PAPERBACK: settings.trade_paperback or settings.default,
            }.get(self.series.format, settings.default),
        )


PATTERN_MAP: dict[str, Callable[[MetronInfo], str | int | None]] = {
    "cover-date": lambda x: x.cover_date,
    "cover-day": lambda x: x.cover_date.day if x.cover_date else None,
    "cover-month": lambda x: x.cover_date.month if x.cover_date else None,
    "cover-year": lambda x: x.cover_date.year if x.cover_date else None,
    "format": lambda x: x.series.format.value if x.series.format else None,
    "id": lambda x: next(iter(i.value for i in x.ids if i.primary), None),
    "imprint": lambda x: x.publisher.imprint.value if x.publisher and x.publisher.imprint else None,
    "isbn": lambda x: x.gtin.isbn if x.gtin else None,
    "issue-count": lambda x: x.series.issue_count,
    "lang": lambda x: x.series.lang,
    "number": lambda x: x.number,
    "publisher-id": lambda x: x.publisher.id if x.publisher else None,
    "publisher-name": lambda x: x.publisher.name if x.publisher else None,
    "series-id": lambda x: x.series.id,
    "series-name": lambda x: x.series.name,
    "series-sort-name": lambda x: x.series.sort_name,
    "series-year": lambda x: x.series.start_year,
    "store-date": lambda x: x.store_date or "",
    "store-year": lambda x: x.store_date.year if x.store_date else "",
    "store-month": lambda x: x.store_date.month if x.store_date else "",
    "store-day": lambda x: x.store_date.day if x.store_date else "",
    "title": lambda x: x.collection_title,
    "upc": lambda x: x.gtin.upc if x.gtin else None,
    "volume": lambda x: x.series.volume,
}
