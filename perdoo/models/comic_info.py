from __future__ import annotations

__all__ = ["YesNo", "Manga", "AgeRating", "PageType", "Page", "ComicInfo"]

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

import xmltodict
from natsort import humansorted, ns
from PIL import Image
from pydantic import Field, HttpUrl

from perdoo.models._base import InfoModel, PascalModel


def str_to_list(value: str | None) -> list[str]:
    if not value:
        return []
    return humansorted({x.replace('"', "").strip() for x in value.split(",")}, alg=ns.NA | ns.G)


def list_to_str(value: list[str]) -> str | None:
    if not value:
        return None
    return ",".join(f'"{x}"' if "," in x else x for x in value)


class YesNo(Enum):
    UNKNOWN = "Unknown"
    NO = "No"
    YES = "Yes"

    @staticmethod
    def load(value: str) -> YesNo:
        for entry in YesNo:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isnt a valid comic_info.YesNo")

    def __lt__(self: YesNo, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: YesNo) -> str:
        return self.value


class Manga(Enum):
    UNKNOWN = "Unknown"
    NO = "No"
    YES = "Yes"
    YES_AND_RIGHT_TO_LEFT = "YesAndRightToLeft"

    @staticmethod
    def load(value: str) -> Manga:
        for entry in Manga:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isnt a valid comic_info.Manga")

    def __lt__(self: Manga, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: Manga) -> str:
        return self.value


class AgeRating(Enum):
    UNKNOWN = "Unknown"
    ADULTS_ONLY = "Adults Only 18+"
    EARLY_CHILDHOOD = "Early Childhood"
    EVERYONE = "Everyone"
    EVERYONE_18 = "Everyone 10+"
    G = "G"
    KIDS_TO_ADULTS = "Kids to Adults"
    M = "M"
    MA = "MA15+"
    MATURE = "Mature 17+"
    PG = "PG"
    R = "R18+"
    RATING_PENDING = "Rating Pending"
    TEEN = "Teen"
    X = "X18+"

    @staticmethod
    def load(value: str) -> AgeRating:
        for entry in AgeRating:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        raise ValueError(f"'{value}' isnt a valid comic_info.AgeRating")

    def __lt__(self: AgeRating, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.value < other.value

    def __str__(self: AgeRating) -> str:
        return self.value


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
        raise ValueError(f"'{value}' isnt a valid comic_info.PageType")

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
    image_width: int | None = Field(alias="@ImageWidth", default=None)
    image_height: int | None = Field(alias="@ImageHeight", default=None)

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


class ComicInfo(PascalModel, InfoModel):
    title: str | None = None
    series: str | None = None
    number: str | None = None
    count: int | None = None
    volume: int | None = None
    alternate_series: str | None = None
    alternate_number: str | None = None
    alternate_count: int | None = None
    summary: str | None = None
    notes: str | None = None
    year: int | None = None
    month: int | None = None
    day: int | None = None
    writer: str | None = None
    penciller: str | None = None
    inker: str | None = None
    colorist: str | None = None
    letterer: str | None = None
    cover_artist: str | None = None
    editor: str | None = None
    publisher: str | None = None
    imprint: str | None = None
    genre: str | None = None
    web: HttpUrl | None = None
    page_count: int = 0
    language_iso: str | None = Field(alias="LanguageISO", default=None)
    format: str | None = None
    black_and_white: YesNo = YesNo.UNKNOWN
    manga: Manga = Manga.UNKNOWN
    characters: str | None = None
    teams: str | None = None
    locations: str | None = None
    scan_information: str | None = None
    story_arc: str | None = None
    series_group: str | None = None
    age_rating: AgeRating = AgeRating.UNKNOWN
    pages: list[Page] = Field(default_factory=list)
    community_rating: float | None = Field(default=None, ge=0, le=5)
    main_character_or_team: str | None = None
    review: str | None = None

    list_fields: ClassVar[dict[str, str]] = {"Pages": "Page"}

    def __init__(self: ComicInfo, **data: Any):
        self.unwrap_list(mappings=ComicInfo.list_fields, content=data)
        super().__init__(**data)

    @property
    def cover_date(self: ComicInfo) -> date | None:
        if not self.year:
            return None
        return date(self.year, self.month or 1, self.day or 1)

    @cover_date.setter
    def cover_date(self: ComicInfo, value: date | None) -> None:
        self.year = value.year if value else None
        self.month = value.month if value else None
        self.day = value.day if value else None

    @property
    def credits(self: ComicInfo) -> dict[str, list[str]]:
        output = {}
        for role, attribute in (
            ("Writer", self.writer),
            ("Penciller", self.penciller),
            ("Inker", self.inker),
            ("Colorist", self.colorist),
            ("Letterer", self.letterer),
            ("Cover Artist", self.cover_artist),
            ("Editor", self.editor),
        ):
            if not attribute:
                continue
            creators = str_to_list(value=attribute)
            for creator in creators:
                output.setdefault(creator, []).append(role)
        return output

    @credits.setter
    def credits(self: ComicInfo, value: dict[str, list[str]]) -> None:
        def get_creators(role: str) -> list[str]:
            return humansorted(
                {
                    creator
                    for creator, roles in value.items()
                    if any(role.casefold() == x.casefold() for x in roles)
                },
                alg=ns.NA | ns.G,
            )

        self.writer = list_to_str(value=get_creators(role="Writer"))
        self.penciller = list_to_str(value=get_creators(role="Penciller"))
        self.inker = list_to_str(value=get_creators(role="Inker"))
        self.colorist = list_to_str(value=get_creators(role="Colorist"))
        self.letterer = list_to_str(value=get_creators(role="Letterers"))
        self.cover_artist = list_to_str(value=get_creators(role="Cover Artist"))
        self.editor = list_to_str(value=get_creators(role="Editor"))

    @property
    def genre_list(self: ComicInfo) -> list[str]:
        return str_to_list(value=self.genre)

    @genre_list.setter
    def genre_list(self: ComicInfo, value: list[str]) -> None:
        self.genre = list_to_str(value=value)

    @property
    def character_list(self: ComicInfo) -> list[str]:
        return str_to_list(value=self.characters)

    @character_list.setter
    def character_list(self: ComicInfo, value: list[str]) -> None:
        self.characters = list_to_str(value=value)

    @property
    def team_list(self: ComicInfo) -> list[str]:
        return str_to_list(value=self.teams)

    @team_list.setter
    def team_list(self: ComicInfo, value: list[str]) -> None:
        self.teams = list_to_str(value=value)

    @property
    def location_list(self: ComicInfo) -> list[str]:
        return str_to_list(value=self.locations)

    @location_list.setter
    def location_list(self: ComicInfo, value: list[str]) -> None:
        self.locations = list_to_str(value=value)

    @property
    def story_arc_list(self: ComicInfo) -> list[str]:
        return str_to_list(value=self.story_arc)

    @story_arc_list.setter
    def story_arc_list(self: ComicInfo, value: list[str]) -> None:
        self.story_arc = list_to_str(value=value)

    @classmethod
    def from_bytes(cls: type[ComicInfo], content: bytes) -> ComicInfo:
        xml_content = xmltodict.parse(content, force_list=list(cls.list_fields.values()))
        return cls(**xml_content["ComicInfo"])

    def to_file(self: ComicInfo, file: Path) -> None:
        content = self.model_dump(by_alias=True, exclude_none=True)
        self.wrap_list(mappings=self.list_fields, content=content)
        content = self.clean_contents(content)
        content["@xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
        content["@xsi:noNamespaceSchemaLocation"] = (
            "https://raw.githubusercontent.com/ComicCorps/Schemas/main/schemas/v2.0/ComicInfo.xsd"
        )

        with file.open("wb") as stream:
            xmltodict.unparse(
                {"ComicInfo": {k: content[k] for k in sorted(content)}},
                output=stream,
                short_empty_elements=True,
                pretty=True,
                indent=" " * 2,
            )
