from __future__ import annotations

__all__ = [
    "Source",
    "Resource",
    "TitledResource",
    "Credit",
    "Format",
    "Series",
    "StoryArc",
    "Issue",
    "Tool",
    "Meta",
    "PageType",
    "Page",
    "Metadata",
]

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import xmltodict
from PIL import Image
from pydantic import Field, PositiveInt

from perdoo import __version__
from perdoo.models._base import InfoModel, PascalModel


class Source(Enum):
    COMICVINE = "Comicvine"
    GRAND_COMICS_DATABASE = "Grand Comics Database"
    LEAGUE_OF_COMIC_GEEKS = "League of Comic Geeks"
    MARVEL = "Marvel"
    METRON = "Metron"

    @staticmethod
    def load(value: str) -> Source:
        for entry in Source:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metadata.Source")

    def __lt__(self: Source, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self: Source) -> str:
        return self.value


class Resource(PascalModel):
    source: Source = Field(alias="@source")
    value: int = Field(alias="#text")

    def __lt__(self: Resource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.source < other.source

    def __eq__(self: Resource, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.source == other.source

    def __hash__(self: Resource) -> int:
        return hash((type(self), self.source))


class TitledResource(PascalModel):
    resources: list[Resource] = Field(default_factory=list)
    title: str

    list_fields: ClassVar[dict[str, str]] = {"Resources": "Resource"}

    def __init__(self: TitledResource, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        super().__init__(**data)

    def __lt__(self: TitledResource, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.title.casefold() < other.title.casefold()

    def __eq__(self: TitledResource, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.title.casefold() == other.title.casefold()

    def __hash__(self: TitledResource) -> int:
        return hash((type(self), self.title.casefold()))


class Credit(PascalModel):
    creator: TitledResource
    roles: list[TitledResource] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {"Roles": "Role"}

    def __init__(self: Credit, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        super().__init__(**data)

    def __lt__(self: Credit, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.creator < other.creator

    def __eq__(self: Credit, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.creator == other.creator

    def __hash__(self: Credit) -> int:
        return hash((type(self), self.creator))


class Format(Enum):
    ANNUAL = "Annual"
    DIGITAL_CHAPTER = "Digital Chapter"
    GRAPHIC_NOVEL = "Graphic Novel"
    HARDCOVER = "Hardcover"
    OMNIBUS = "Omnibus"
    SINGLE_ISSUE = "Single Issue"
    TRADE_PAPERBACK = "Trade Paperback"

    @staticmethod
    def load(value: str) -> Format:
        for entry in Format:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metadata.Format")

    def __lt__(self: Format, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self: Format) -> str:
        return self.value


class Series(TitledResource):
    genres: list[TitledResource] = Field(default_factory=list)
    publisher: TitledResource
    start_year: int | None = None
    volume: PositiveInt = Field(default=1)

    list_fields: ClassVar[dict[str, str]] = {**TitledResource.list_fields, "Genres": "Genre"}

    def __init__(self: Series, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        super().__init__(**data)

    def __lt__(self: Series, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        if self.publisher != other.publisher:
            return self.publisher < other.publisher
        if self.title.casefold() != other.title.casefold():
            return self.title.casefold() < other.title.casefold()
        return self.volume < other.volume

    def __eq__(self: Series, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.publisher, self.title.casefold(), self.volume) == (
            other.publisher,
            other.title.casefold(),
            other.volume,
        )

    def __hash__(self: Series) -> int:
        return hash((type(self), self.publisher, self.title.casefold(), self.volume))


class StoryArc(TitledResource):
    number: int | None = None


class Issue(PascalModel):
    characters: list[TitledResource] = Field(default_factory=list)
    cover_date: date | None = None
    credits: list[Credit] = Field(default_factory=list)
    format: Format = Format.SINGLE_ISSUE
    language: str = Field(alias="@language", default="en")
    locations: list[TitledResource] = Field(default_factory=list)
    number: str | None = None
    page_count: int = 0
    resources: list[Resource] = Field(default_factory=list)
    series: Series
    store_date: date | None = None
    story_arcs: list[StoryArc] = Field(default_factory=list)
    summary: str | None = None
    teams: list[TitledResource] = Field(default_factory=list)
    title: str | None = None

    list_fields: ClassVar[dict[str, str]] = {
        **Series.list_fields,
        **Credit.list_fields,
        **TitledResource.list_fields,
        "Characters": "Character",
        "Credits": "Credit",
        "Genres": "Genre",
        "Locations": "Location",
        "Resources": "Resource",
        "StoryArcs": "StoryArc",
        "Teams": "Team",
    }

    def __init__(self: Issue, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        super().__init__(**data)

    def __lt__(self: Issue, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        if self.series != other.series:
            return self.series < other.series
        if self.number.casefold() != other.number.casefold():
            return self.number.casefold() < other.number.casefold()
        return self.format < other.format

    def __eq__(self: Issue, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self.series, self.number.casefold(), self.format) == (
            other.series,
            other.number.casefold(),
            other.format,
        )

    def __hash__(self: Issue) -> int:
        return hash((type(self), self.series, self.number.casefold(), self.format))


class Tool(PascalModel):
    version: str = Field(alias="@version", default=__version__)
    value: str = Field(alias="#text", default="Perdoo")


class Meta(PascalModel):
    date_: date = Field(alias="@date")
    tool: Tool = Field(default_factory=Tool)


class PageType(Enum):
    ADVERTISEMENT = "Advertisement"
    BACK_COVER = "Back Cover"
    EDITORIAL = "Editorial"
    FRONT_COVER = "Front Cover"
    INNER_COVER = "Inner Cover"
    LETTERS = "Letters"
    OTHER = "Other"
    PREVIEW = "Preview"
    ROUNDUP = "Roundup"
    STORY = "Story"

    @staticmethod
    def load(value: str) -> PageType:
        for entry in PageType:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"`{value}` isn't a valid metadata.PageType")

    def __lt__(self: PageType, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.value < other.value

    def __str__(self: PageType) -> str:
        return self.value


class Page(PascalModel):
    double_page: bool = Field(alias="@doublePage", default=False)
    filename: str = Field(alias="@filename")
    height: int = Field(alias="@height")
    index: int = Field(alias="@index")
    size: int = Field(alias="@size")
    type: PageType = Field(alias="@type", default=PageType.STORY)
    width: int = Field(alias="@width")

    def __lt__(self: Page, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.index < other.index

    def __eq__(self: Page, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.filename == other.filename

    def __hash__(self: Page) -> int:
        return hash((type(self), self.filename))

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
            double_page=width >= height,
            filename=file.name,
            height=height,
            index=index,
            size=file.stat().st_size,
            type=page_type,
            width=width,
        )


class Metadata(PascalModel, InfoModel):
    issue: Issue
    meta: Meta
    notes: str | None = None
    pages: list[Page] = Field(default_factory=list)

    list_fields: ClassVar[dict[str, str]] = {**Issue.list_fields, "Pages": "Page"}

    def __init__(self: Metadata, **data: Any):
        self.unwrap_list(mappings=self.list_fields, content=data)
        super().__init__(**data)

    def __lt__(self: Metadata, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.issue < other.issue

    def __eq__(self: Metadata, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.issue == other.issue

    def __hash__(self: Metadata) -> int:
        return hash((type(self), self.issue))

    @classmethod
    def from_bytes(cls: type[Metadata], content: bytes) -> Metadata:
        xml_content = xmltodict.parse(content, force_list=list(cls.list_fields.values()))
        return cls(**xml_content["Metadata"])

    def to_file(self: Metadata, file: Path) -> None:
        content = self.model_dump(by_alias=True, exclude_none=True)
        self.wrap_list(mappings=self.list_fields, content=content)
        content = self.clean_contents(content)
        content["@xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
        content["@xsi:noNamespaceSchemaLocation"] = (
            "https://raw.githubusercontent.com/Buried-In-Code/Schemas/main/drafts/v1.0/Metadata.xsd"
        )

        with file.open("wb") as stream:
            xmltodict.unparse(
                {"Metadata": {k: content[k] for k in sorted(content)}},
                output=stream,
                short_empty_elements=True,
                pretty=True,
                indent=" " * 2,
            )
