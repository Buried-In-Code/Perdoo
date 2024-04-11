from __future__ import annotations

__all__ = [
    "GTIN",
    "AgeRating",
    "Arc",
    "Credit",
    "Format",
    "Genre",
    "GenreResource",
    "InformationSource",
    "MetronInfo",
    "Price",
    "Resource",
    "Role",
    "RoleResource",
    "Series",
    "Source",
    "Sources",
    "Universe",
]

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import xmltodict
from PIL import Image
from pydantic import Field, HttpUrl, PositiveInt

from perdoo.models._base import InfoModel, PascalModel


class InformationSource(Enum):
    COMIC_VINE = "Comic Vine"
    GRAND_COMICS_DATABASE = "Grand Comics Database"
    MARVEL = "Marvel"
    METRON = "Metron"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"

    @staticmethod
    def load(value: str) -> InformationSource:
        for entry in InformationSource:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.InformationSource")

    def __lt__(self: InformationSource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: InformationSource) -> str:
        return self.value


class Source(PascalModel):
    source: InformationSource = Field(alias="@source")
    value: PositiveInt = Field(alias="#text")

    def __lt__(self: Source, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.source < other.source

    def __eq__(self: Source, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.source == other.source

    def __hash__(self: Source) -> int:
        return hash((type(self), self.source))


class Sources(PascalModel):
    primary: Source
    alternative: list[Source] = Field(default_factory=list)


class Resource(PascalModel):
    id: PositiveInt | None = Field(alias="@id", default=None)
    value: str = Field(alias="#text")

    def __lt__(self: Resource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __eq__(self: Resource, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value == other.value

    def __hash__(self: Resource) -> int:
        return hash((type(self), self.value))


class Format(Enum):
    ANNUAL = "Annual"
    GRAPHIC_NOVEL = "Graphic Novel"
    LIMITED_SERIES = "Limited Series"
    ONE_SHOT = "One-Shot"
    SERIES = "Series"
    TRADE_PAPERBACK = "Trade Paperback"
    HARDCOVER = "Hardcover"

    @staticmethod
    def load(value: str) -> Format:
        for entry in Format:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        # region Manual matches
        if value.casefold() in ["Cancelled Series".casefold(), "Ongoing Series".casefold()]:
            return Format.SERIES
        # endregion
        raise ValueError(f"`{value}` isn't a valid metron_info.Format")

    def __lt__(self: Format, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: Format) -> str:
        return self.value


class Series(PascalModel):
    id: PositiveInt | None = Field(alias="@id", default=None)
    lang: str = Field(alias="@lang", default="en")
    name: str
    sort_name: str | None = None
    volume: int | None = None
    format: Format | None = None


class Price(PascalModel):
    country: str = Field(alias="@country")
    value: float = Field(alias="#text")

    def __lt__(self: Price, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.country < other.country

    def __eq__(self: Price, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.country == other.country

    def __hash__(self: Price) -> int:
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
    def load(value: str) -> Genre:
        for entry in Genre:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.Genre")

    def __lt__(self: Genre, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: Genre) -> str:
        return self.value


class GenreResource(PascalModel):
    id: PositiveInt | None = Field(alias="@id", default=None)
    value: Genre = Field(alias="#text")

    def __lt__(self: GenreResource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __eq__(self: GenreResource, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value == other.value

    def __hash__(self: GenreResource) -> int:
        return hash((type(self), self.value))


class Arc(PascalModel):
    id: PositiveInt | None = Field(alias="@id", default=None)
    name: str
    number: PositiveInt | None = None

    def __lt__(self: Arc, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.name < other.name

    def __eq__(self: Arc, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.name == other.name

    def __hash__(self: Arc) -> int:
        return hash((type(self), self.name))


class Universe(PascalModel):
    id: int | None = Field(alias="@id", default=None, gt=0)
    name: str
    designation: str | None = None

    def __lt__(self: Universe, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.name < other.name

    def __eq__(self: Universe, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.name == other.name

    def __hash__(self: Universe) -> int:
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
    def load(value: str) -> AgeRating:
        for entry in AgeRating:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.AgeRating")

    def __lt__(self: AgeRating, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: AgeRating) -> str:
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
    def load(value: str) -> Role:
        for entry in Role:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.Role")

    def __lt__(self: Role, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: Role) -> str:
        return self.value


class RoleResource(PascalModel):
    id: PositiveInt | None = Field(alias="@id", default=None)
    value: Role = Field(alias="#text")

    def __lt__(self: RoleResource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __eq__(self: RoleResource, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value == other.value

    def __hash__(self: RoleResource) -> int:
        return hash((type(self), self.value))


class Credit(PascalModel):
    creator: Resource
    roles: list[RoleResource] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {"Roles": "Role"}
    text_fields: ClassVar[list[str]] = ["Creator", "Roles"]

    def __init__(self: Credit, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        self.to_xml_text(mappings=self.text_fields, content=data)
        super().__init__(**data)

    def __lt__(self: Credit, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.creator < other.creator

    def __eq__(self: Credit, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.creator == other.creator

    def __hash__(self: Credit) -> int:
        return hash((type(self), self.creator))


class PageType(Enum):
    FRONT_COVER = "FrontCover"
    INNER_COVER = "InnerCover"
    ROUNDUP = "Roundup"
    STORY = "Story"
    ADVERTISEMENT = "Advertisement"
    EDITORIAL = "Editorial"
    LETTERS = "Letters"
    PREVIEW = "Preview"
    BACK_COVER = "BackCover"
    OTHER = "Other"
    DELETED = "Deleted"

    @staticmethod
    def load(value: str) -> PageType:
        for entry in PageType:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metron_info.PageType")

    def __lt__(self: PageType, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: PageType) -> str:
        return self.value


class Page(PascalModel):
    image: int = Field(alias="@Image")
    type: PageType = Field(alias="@Type", default=PageType.STORY)
    double_page: bool = Field(alias="@DoublePage", default=False)
    image_size: int = Field(alias="@ImageSize", default=0)
    key: str | None = Field(alias="@Key", default=None)
    bookmark: str | None = Field(alias="@Bookmark", default=None)
    image_height: int | None = Field(alias="@ImageHeight", default=None)
    image_width: int | None = Field(alias="@ImageWidth", default=None)

    def __lt__(self: Page, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.image < other.image

    def __eq__(self: Page, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.image == other.image

    def __hash__(self: Page) -> int:
        return hash((type(self), self.image))

    @staticmethod
    def from_path(file: Path, index: int, is_final_page: bool, page: Page | None) -> Page:
        if page:
            page_type = page.type
        elif index == 0:
            page_type = PageType.FRONT_COVER
        elif is_final_page:
            page_type = PageType.BACK_COVER
        else:
            page_type = PageType.STORY
        with Image.open(file) as img:
            width, height = img.size
        return Page(
            image=index,
            type=page_type,
            double_page=width >= height,
            image_size=file.stat().st_size,
            image_height=height,
            image_width=width,
        )


class MetronInfo(PascalModel, InfoModel):
    id: Sources | None = Field(alias="ID", default=None)
    publisher: Resource
    series: Series
    collection_title: str | None = None
    number: str | None = None
    stories: list[Resource] = Field(default_factory=list)
    summary: str | None = None
    notes: str | None = None
    prices: list[Price] = Field(default_factory=list)
    cover_date: date | None = None
    store_date: date | None = None
    page_count: int = 0
    genres: list[GenreResource] = Field(default_factory=list)
    tags: list[Resource] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)
    characters: list[Resource] = Field(default_factory=list)
    teams: list[Resource] = Field(default_factory=list)
    universes: list[Universe] = Field(default_factory=list)
    locations: list[Resource] = Field(default_factory=list)
    gtin: GTIN | None = Field(alias="GTIN", default=None)
    age_rating: AgeRating = Field(default=AgeRating.UNKNOWN)
    reprints: list[Resource] = Field(default_factory=list)
    url: HttpUrl | None = Field(alias="URL", default=None)
    credits: list[Credit] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {
        **Credit.list_fields,
        "Stories": "Story",
        "Prices": "Price",
        "Genres": "Genre",
        "Tags": "Tag",
        "Arcs": "Arc",
        "Characters": "Character",
        "Teams": "Team",
        "Universes": "Universe",
        "Locations": "Location",
        "Reprints": "Reprint",
        "Credits": "Credit",
        "Pages": "Page",
    }
    text_fields: ClassVar[list[str]] = [
        "Source",
        "Publisher",
        "Stories",
        "Prices",
        "Genres",
        "Tags",
        "Characters",
        "Teams",
        "Locations",
        "Reprints",
    ]

    def __init__(self: MetronInfo, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        self.to_xml_text(mappings=self.text_fields, content=data)
        super().__init__(**data)

    @classmethod
    def from_bytes(cls: type[MetronInfo], content: bytes) -> MetronInfo:
        xml_content = xmltodict.parse(content, force_list=list(cls.list_fields.values()))
        return cls(**xml_content["MetronInfo"])

    def to_file(self: MetronInfo, file: Path) -> None:
        content = self.model_dump(by_alias=True, exclude_none=True)
        self.wrap_list(mappings=self.list_fields, content=content)
        content = self.clean_contents(content)
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
