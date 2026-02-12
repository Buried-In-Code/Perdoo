from datetime import date, datetime

import pytest

from perdoo.comic.metadata import MetronInfo
from perdoo.comic.metadata.metron_info import (
    GTIN,
    Credit,
    Format,
    Id,
    InformationSource,
    Publisher,
    Resource,
    Role,
)
from perdoo.settings import Naming


def test_information_source_load_valid() -> None:
    assert InformationSource.load(value="Metron") is InformationSource.METRON
    assert InformationSource.load(value="Comic Vine") is InformationSource.COMIC_VINE
    with pytest.raises(ValueError, match=r"isn't a valid InformationSource"):
        InformationSource.load(value="Not Real")


def test_role_load_unknown_fallback() -> None:
    assert Role.load(value="Writer") is Role.WRITER
    assert Role.load(value="Not Real") is Role.OTHER


def test_ensure_timezone_adds_local_tz(metron_info: MetronInfo) -> None:
    naive = datetime(2020, 1, 1, 12, 0, 0)  # tzinfo=None
    metron_info.last_modified = naive

    assert metron_info.last_modified is not None
    assert metron_info.last_modified.tzinfo is not None


def test_get_filename_padding_and_sanitization(metron_info: MetronInfo) -> None:
    metron_info.number = 2
    metron_info.cover_date = date(2021, 7, 4)
    metron_info.ids = [
        Id(primary=False, source=InformationSource.METRON, value="abc"),
        Id(primary=True, source=InformationSource.COMIC_VINE, value="cv-123"),
    ]
    settings = Naming(
        seperator="-",
        default="{publisher-name}/{series-name}-v{volume}/{series-name}-v{volume}_#{number:03}_{cover-year}_{id}",
    )
    name = metron_info.get_filename(settings=settings)

    assert "#002" in name
    assert "2021" in name
    assert "cv-123" in name


def test_pattern_map(metron_info: MetronInfo) -> None:
    metron_info.publisher = Publisher(name="Pub", imprint=Resource(value="Imprint Name"))
    metron_info.gtin = GTIN(isbn="9781234567890", upc="012345678905")
    settings = Naming(seperator="-", default="{publisher-name}/{imprint}/{isbn}/{upc}")
    name = metron_info.get_filename(settings=settings)

    assert "Pub" in name
    assert "Imprint-Name" in name
    assert "9781234567890" in name
    assert "012345678905" in name


def test_xml_bytes_preserved(metron_info: MetronInfo) -> None:
    metron_info.credits = [
        Credit(
            creator=Resource(value="Alice"),
            roles=[Resource(value=Role.WRITER), Resource(value=Role.INKER)],
        )
    ]
    metron_info.series.format = Format.SINGLE_ISSUE
    metron_info.number = 2
    loaded = MetronInfo.from_bytes(content=metron_info.to_bytes())

    assert loaded.series.name == metron_info.series.name
    assert loaded.series.format == metron_info.series.format
    assert loaded.number == metron_info.number
    assert loaded.credits[0].creator.value == metron_info.credits[0].creator.value
    assert {r.value for r in loaded.credits[0].roles} == {
        r.value for r in metron_info.credits[0].roles
    }
