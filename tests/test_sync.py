from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from perdoo.cli import sync


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz: timezone | None = None) -> datetime:
        return datetime(2026, 9, 4, tzinfo=tz or timezone.utc)


@pytest.fixture(autouse=True)
def freeze_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync, "datetime", FixedDatetime)


@pytest.mark.parametrize(
    ("last_modified", "days", "expected"),
    [
        (datetime(2026, 9, 4, tzinfo=timezone.utc), 28, False),
        (datetime(2026, 8, 7, tzinfo=timezone.utc), 28, True),
        (datetime(2026, 8, 8, tzinfo=timezone.utc), 28, False),
    ],
    ids=["updated-today", "at-sync-threshold", "below-sync-threshold"],
)
def test_should_sync_uses_the_metron_last_modified_date(
    last_modified: datetime, days: int, expected: bool
) -> None:
    metron_info = SimpleNamespace(last_modified=last_modified)

    assert sync.should_sync(metron_info, None, days) is expected


def test_should_sync_uses_the_comic_info_note_when_metron_info_is_missing() -> None:
    comic_info = SimpleNamespace(
        notes=(
            "Tagged with Perdoo v2026.2.0 using info from Metron at 2026-08-07T12:00:00+00:00. [issue_id:123]"  # noqa: E501
        )
    )

    assert sync.should_sync(None, comic_info, 28) is True


def test_should_sync_without_any_previous_metadata() -> None:
    assert sync.should_sync(None, None, 28) is True
