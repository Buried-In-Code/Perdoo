from datetime import date

from perdoo.comic.metadata import ComicInfo
from perdoo.comic.metadata.comic_info import Page, PageType
from perdoo.settings import Naming


def test_cover_date_property(comic_info: ComicInfo) -> None:
    assert comic_info.cover_date is None

    comic_info.cover_date = date(2020, 2, 29)
    assert comic_info.year == 2020
    assert comic_info.month == 2
    assert comic_info.day == 29
    assert comic_info.cover_date == date(2020, 2, 29)

    comic_info.year = None
    assert comic_info.year is None
    assert comic_info.month == 2
    assert comic_info.day == 29
    assert comic_info.cover_date is None


def test_page_ordering_and_hashing() -> None:
    p1 = Page(image=2, type=PageType.STORY)
    p2 = Page(image=1, type=PageType.FRONT_COVER)
    p3 = Page(image=2, type=PageType.OTHER)

    assert sorted([p1, p2]) == [p2, p1]
    assert p1 == p3
    assert len({p1, p2, p3}) == 2


def test_credits_property(comic_info: ComicInfo) -> None:
    comic_info.credits = {
        "Alice": ["Writer"],
        "Bob": ["Inker", "Colorist"],
        "Charles": ["Writer", "Inker"],
    }

    assert comic_info.writer == "Alice,Charles"
    assert comic_info.inker == "Bob,Charles"
    assert comic_info.colorist == "Bob"


def test_list_fields_mapping(comic_info: ComicInfo) -> None:
    comic_info.genre_list = ["Sci-Fi", "Noir"]
    comic_info.character_list = ["Alice", "Bob"]
    comic_info.team_list = ["Team X"]
    comic_info.location_list = ["Gotham"]
    comic_info.story_arc_list = ["Arc 1", "Arc 2"]

    assert comic_info.genre == "Sci-Fi,Noir"
    assert comic_info.characters == "Alice,Bob"
    assert comic_info.teams == "Team X"
    assert comic_info.locations == "Gotham"
    assert comic_info.story_arc == "Arc 1,Arc 2"


def test_get_filename_padding_and_sanitization() -> None:
    obj = ComicInfo(
        publisher="Example Publisher",
        series="Example Series",
        volume=1,
        number=2,
        format="Single Issue",
        title="Hello: World / ???",
    )
    settings = Naming(
        seperator="-",
        default="{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_#{number:02}-{title}",
    )
    name = obj.get_filename(settings=settings)

    assert "#02" in name
    assert "Hello-World" in name


def test_xml_bytes_preserves_pages() -> None:
    obj = ComicInfo(
        series="Series",
        number=1,
        format="Single Issue",
        pages=[
            Page(image=1, type=PageType.FRONT_COVER, image_size=123),
            Page(image=2, type=PageType.STORY, image_size=456),
        ],
    )
    loaded = ComicInfo.from_bytes(content=obj.to_bytes())

    assert loaded.series == obj.series
    assert len(loaded.pages) == len(obj.pages)
    assert loaded.pages[0].image == obj.pages[0].image
    assert loaded.pages[0].type == obj.pages[0].type
    assert loaded.pages[1].image == obj.pages[1].image
    assert loaded.pages[1].type == obj.pages[1].type
