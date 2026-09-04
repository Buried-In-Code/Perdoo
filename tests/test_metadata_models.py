from datetime import datetime, timezone

import pytest
from shortbox.metadata import ComicInfo
from shortbox.metadata.metron_info import InformationSource

from perdoo.services._models import (
    get_comic_info_note_id,
    get_comic_info_note_modified,
    search_from_comic_info,
    set_comic_info_note_id,
)


@pytest.mark.parametrize(
    ("notes", "source", "expected"),
    [
        (
            (
                "Tagged with Perdoo v2026.2.0 using info from Comic Vine at 2026-09-04T12:00:00+00:00. [issue_id:123]"  # noqa: E501
            ),
            InformationSource.COMIC_VINE,
            123,
        ),
        (
            (
                "Tagged with MetronTagger-1.0 using info from Metron on 2026-09-04 12:00:00. [issue_id:456]"  # noqa: E501
            ),
            InformationSource.METRON,
            456,
        ),
        (
            "Tagged with ComicTagger using Comic Vine issue id 789",
            InformationSource.COMIC_VINE,
            789,
        ),
    ],
    ids=["perdoo", "metron-tagger", "comic-tagger"],
)
def test_get_comic_info_note_id_recognizes_supported_taggers(
    notes: str, source: InformationSource, expected: int
) -> None:
    assert get_comic_info_note_id(notes, source) == expected


def test_get_comic_info_note_id_requires_the_requested_source() -> None:
    notes = "Tagged with Perdoo v2026.2.0 using info from Comic Vine at 2026-09-04T12:00:00+00:00. [issue_id:123]"  # noqa: E501

    assert get_comic_info_note_id(notes, InformationSource.METRON) is None


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        (
            (
                "Tagged with Perdoo v2026.2.0 using info from Metron at 2026-09-04T12:00:00+00:00. [issue_id:123]"  # noqa: E501
            ),
            datetime(2026, 9, 4, 12, tzinfo=timezone.utc),
        ),
        (
            (
                "Tagged with MetronTagger-1.0 using info from Metron on 2026-09-04 12:00:00. [issue_id:456]"  # noqa: E501
            ),
            "2026-09-04T12:00:00",
        ),
        ("Tagged with Perdoo v1 using info from Metron at invalid. [issue_id:123]", None),
    ],
    ids=["perdoo-iso-timestamp", "metron-tagger-timestamp", "invalid-timestamp"],
)
def test_get_comic_info_note_modified_parses_supported_dates(
    notes: str, expected: datetime | str | None
) -> None:
    modified = get_comic_info_note_modified(notes)

    if isinstance(expected, str):
        assert modified is not None
        assert modified.isoformat() == expected
    else:
        assert modified == expected


def test_set_comic_info_note_id_records_source_identifier_and_timestamp() -> None:
    metadata = ComicInfo()
    modified = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)

    set_comic_info_note_id(metadata, InformationSource.METRON, 456, modified)

    assert metadata.notes == (
        "Tagged with Perdoo v2026.2.0 using info from Metron at 2026-09-04T12:00:00+00:00. [issue_id:456]"  # noqa: E501
    )


@pytest.mark.parametrize(
    ("volume", "expected_volume", "expected_year"),
    [(3, 3, None), (2024, None, 2024)],
    ids=["volume-number", "publication-year"],
)
def test_search_from_comic_info_distinguishes_volume_numbers_from_years(
    volume: int, expected_volume: int | None, expected_year: int | None
) -> None:
    metadata = ComicInfo(series="Spider-Man", number="1", volume=volume)

    result = search_from_comic_info(metadata, filename="Spider-Man 001")

    assert result.series.name == "Spider-Man"
    assert result.series.volume == expected_volume
    assert result.series.year == expected_year
    assert result.issue.number == "1"
