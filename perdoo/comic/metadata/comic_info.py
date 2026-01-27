__all__ = ["AgeRating", "ComicInfo", "Manga", "Page", "PageType", "YesNo"]

import logging
from collections.abc import Callable
from datetime import date
from enum import Enum
from typing import ClassVar

from natsort import humansorted, ns
from pydantic import HttpUrl, NonNegativeFloat
from pydantic_xml import attr, computed_attr, element, wrapped

from perdoo.comic.metadata._base import Metadata, PascalModel
from perdoo.settings import Naming

LOGGER = logging.getLogger(__name__)


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
    def load(value: str) -> "YesNo":
        for entry in YesNo:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        LOGGER.warning("'%s' isn't a valid YesNo", value)
        return YesNo.UNKNOWN

    def __str__(self) -> str:
        return self.value


class Manga(Enum):
    UNKNOWN = "Unknown"
    NO = "No"
    YES = "Yes"
    YES_AND_RIGHT_TO_LEFT = "YesAndRightToLeft"

    @staticmethod
    def load(value: str) -> "Manga":
        for entry in Manga:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        LOGGER.warning("'%s' isn't a valid Manga", value)
        return Manga.UNKNOWN

    def __str__(self) -> str:
        return self.value


class AgeRating(Enum):
    UNKNOWN = "Unknown"
    ADULTS_ONLY = "Adults Only 18+"
    EARLY_CHILDHOOD = "Early Childhood"
    EVERYONE = "Everyone"
    EVERYONE_10 = "Everyone 10+"
    G = "G"
    KIDS_TO_ADULTS = "Kids to Adults"
    M = "M"
    MA15 = "MA15+"
    MATURE_17 = "Mature 17+"
    PG = "PG"
    R18 = "R18+"
    RATING_PENDING = "Rating Pending"
    TEEN = "Teen"
    X18 = "X18+"

    @staticmethod
    def load(value: str) -> "AgeRating":
        for entry in AgeRating:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        LOGGER.warning("'%s' isn't a valid AgeRating", value)
        return AgeRating.UNKNOWN

    def __str__(self) -> str:
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
    def load(value: str) -> "PageType":
        for entry in PageType:
            if entry.value.replace(" ", "").casefold() == value.replace(" ", "").casefold():
                return entry
        LOGGER.warning("'%s' isn't a valid PageType", value)
        return PageType.OTHER

    def __str__(self) -> str:
        return self.value


class Page(PascalModel):
    bookmark: str | None = attr(default=None)
    double_page: bool = attr(default=False)
    image: int = attr()
    image_height: int | None = attr(default=None)
    image_size: int = attr(default=0)
    image_width: int | None = attr(default=None)
    key: str | None = attr(default=None)
    type: PageType = attr(default=PageType.STORY)

    def __lt__(self, other) -> int:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.image < other.image

    def __eq__(self, other) -> bool:  # noqa: ANN001
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.image == other.image

    def __hash__(self) -> int:
        return hash((type(self), self.image))


class ComicInfo(Metadata):
    FILENAME: ClassVar[str] = "ComicInfo.xml"

    age_rating: AgeRating = element(default=AgeRating.UNKNOWN)
    alternate_count: int | None = element(default=None)
    alternate_number: str | None = element(default=None)
    alternate_series: str | None = element(default=None)
    black_and_white: YesNo = element(default=YesNo.UNKNOWN)
    characters: str | None = element(default=None)
    colorist: str | None = element(default=None)
    community_rating: NonNegativeFloat | None = element(default=None, le=5)
    count: int | None = element(default=None)
    cover_artist: str | None = element(default=None)
    day: int | None = element(default=None)
    editor: str | None = element(default=None)
    format: str | None = element(default=None)
    genre: str | None = element(default=None)
    imprint: str | None = element(default=None)
    inker: str | None = element(default=None)
    language_iso: str | None = element(tag="LanguageISO", default=None)
    letterer: str | None = element(default=None)
    locations: str | None = element(default=None)
    main_character_or_team: str | None = element(default=None)
    manga: Manga = element(default=Manga.UNKNOWN)
    month: int | None = element(default=None)
    notes: str | None = element(default=None)
    number: str | None = element(default=None)
    page_count: int = element(default=0)
    pages: list[Page] = wrapped(path="Pages", entity=element(tag="Page", default_factory=list))
    penciller: str | None = element(default=None)
    publisher: str | None = element(default=None)
    review: str | None = element(default=None)
    scan_information: str | None = element(default=None)
    series: str | None = element(default=None)
    series_group: str | None = element(default=None)
    story_arc: str | None = element(default=None)
    summary: str | None = element(default=None)
    teams: str | None = element(default=None)
    title: str | None = element(default=None)
    volume: int | None = element(default=None)
    web: HttpUrl | None = element(default=None)
    writer: str | None = element(default=None)
    year: int | None = element(default=None)

    @computed_attr(ns="xsi", name="noNamespaceSchemaLocation")
    def schema_location(self) -> str:
        return "https://raw.githubusercontent.com/anansi-project/comicinfo/main/schema/v2.0/ComicInfo.xsd"

    @property
    def cover_date(self) -> date | None:
        if not self.year:
            return None
        return date(self.year, self.month or 1, self.day or 1)

    @cover_date.setter
    def cover_date(self, value: date | None) -> None:
        self.year = value.year if value else None
        self.month = value.month if value else None
        self.day = value.day if value else None

    @property
    def credits(self) -> dict[str, list[str]]:
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
    def credits(self, value: dict[str, list[str]]) -> None:
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
    def genre_list(self) -> list[str]:
        return str_to_list(value=self.genre)

    @genre_list.setter
    def genre_list(self, value: list[str]) -> None:
        self.genre = list_to_str(value=value)

    @property
    def character_list(self) -> list[str]:
        return str_to_list(value=self.characters)

    @character_list.setter
    def character_list(self, value: list[str]) -> None:
        self.characters = list_to_str(value=value)

    @property
    def team_list(self) -> list[str]:
        return str_to_list(value=self.teams)

    @team_list.setter
    def team_list(self, value: list[str]) -> None:
        self.teams = list_to_str(value=value)

    @property
    def location_list(self) -> list[str]:
        return str_to_list(value=self.locations)

    @location_list.setter
    def location_list(self, value: list[str]) -> None:
        self.locations = list_to_str(value=value)

    @property
    def story_arc_list(self) -> list[str]:
        return str_to_list(value=self.story_arc)

    @story_arc_list.setter
    def story_arc_list(self, value: list[str]) -> None:
        self.story_arc = list_to_str(value=value)

    def get_filename(self, settings: Naming) -> str:
        from perdoo.comic.metadata.metron_info import Format  # noqa: PLC0415

        return self.evaluate_pattern(
            pattern_map=PATTERN_MAP,
            pattern={
                Format.ANNUAL.value: settings.annual or settings.default,
                Format.DIGITAL_CHAPTER.value: settings.digital_chapter or settings.default,
                Format.GRAPHIC_NOVEL.value: settings.graphic_novel or settings.default,
                Format.HARDCOVER.value: settings.hardcover or settings.default,
                Format.LIMITED_SERIES.value: settings.limited_series or settings.default,
                Format.OMNIBUS.value: settings.omnibus or settings.default,
                Format.ONE_SHOT.value: settings.one_shot or settings.default,
                Format.SINGLE_ISSUE.value: settings.single_issue or settings.default,
                Format.TRADE_PAPERBACK.value: settings.trade_paperback or settings.default,
            }.get(self.format, settings.default),
            seperator=settings.seperator,
        )


PATTERN_MAP: dict[str, Callable[[ComicInfo], str | int | None]] = {
    "cover-date": lambda x: x.cover_date,
    "cover-day": lambda x: x.day,
    "cover-month": lambda x: x.month,
    "cover-year": lambda x: x.year,
    "format": lambda x: x.format,
    "id": lambda _: None,
    "imprint": lambda x: x.imprint,
    "isbn": lambda _: None,
    "issue-count": lambda x: x.count,
    "lang": lambda x: x.language_iso,
    "number": lambda x: x.number,
    "publisher-id": lambda _: None,
    "publisher-name": lambda x: x.publisher,
    "series-id": lambda _: None,
    "series-name": lambda x: x.series,
    "series-sort-name": lambda _: None,
    "series-year": lambda x: x.volume if x.volume and x.volume > 1900 else None,
    "store-date": lambda _: None,
    "store-day": lambda _: None,
    "store-month": lambda _: None,
    "store-year": lambda _: None,
    "title": lambda x: x.title,
    "upc": lambda _: None,
    "volume": lambda x: x.volume if x.volume and x.volume < 1900 else None,
}
