import pytest

from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata.metron_info import Series


@pytest.fixture
def metron_info() -> MetronInfo:
    return MetronInfo(series=Series(name="Test Series"))


@pytest.fixture
def comic_info() -> ComicInfo:
    return ComicInfo()
