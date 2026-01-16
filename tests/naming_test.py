from perdoo.comic.metadata import ComicInfo, MetronInfo
from perdoo.comic.metadata._base import sanitize
from perdoo.comic.metadata.metron_info import Format, Publisher, Series
from perdoo.settings import Naming


def test_sanitize() -> None:
    assert sanitize("Example Title!", seperator="-") == "Example-Title!"
    assert sanitize("Example/Title: 123", seperator="-") == "ExampleTitle-123"
    assert sanitize("!@#$%^&*()[]{};':,.<>?/", seperator="-") == "!&"
    assert sanitize(None, seperator="-") is None


def test_metron_info_default_naming() -> None:
    obj = MetronInfo(
        publisher=Publisher(name="Example Publisher"),
        series=Series(name="Example Series", volume=1, format=Format.TRADE_PAPERBACK),
        number=2,
    )
    assert (
        obj.get_filename(settings=Naming())
        == "Example-Publisher/Example-Series-v1/Example-Series-v1_TPB_#02"
    )


def test_comic_info_default_naming() -> None:
    obj = ComicInfo(
        publisher="Example Publisher",
        series="Example Series",
        format="Trade Paperback",
        volume=1,
        number=2,
    )
    assert (
        obj.get_filename(settings=Naming())
        == "Example-Publisher/Example-Series-v1/Example-Series-v1_TPB_#02"
    )
