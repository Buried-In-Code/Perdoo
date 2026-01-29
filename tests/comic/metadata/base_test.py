from pathlib import Path

from perdoo.comic.metadata import ComicInfo
from perdoo.comic.metadata._base import sanitize
from perdoo.settings import Naming


def test_sanitize_basic() -> None:
    assert sanitize(value="Example Title!", seperator="-") == "Example-Title!"
    assert sanitize(value="Example/Title: 123", seperator="-") == "ExampleTitle-123"
    assert sanitize(value=" already  spaced ", seperator="_") == "already_spaced"


def test_sanitize_none_and_empty() -> None:
    assert sanitize(value=None, seperator="-") is None
    assert sanitize(value="", seperator="-") == ""


def test_evaluate_pattern() -> None:
    obj = ComicInfo(series="Series", volume=1, number=2, format="Single Issue", publisher="Pub")
    settings = Naming(seperator="-", default="{series-name}-{unknown}-{number:03}")
    name = obj.get_filename(settings=settings)

    assert name == "Series-unknown-002"


def test_metadata_to_file(tmp_path: Path) -> None:
    obj = ComicInfo(series="Example", number=1, format="Single Issue")
    out = tmp_path / obj.FILENAME
    obj.to_file(file=out)

    assert out.exists()

    loaded = ComicInfo.from_bytes(content=out.read_bytes())

    assert loaded.series == "Example"
    assert loaded.number == "1"
    assert loaded.format == "Single Issue"
