from perdoo.metadata._base import sanitize
from perdoo.metadata.comic_info import ComicInfo
from perdoo.metadata.metron_info import Format, MetronInfo, Publisher, Series
from perdoo.settings import Naming


def test_sanitize() -> None:
    assert sanitize("Example Title!") == "Example-Title!"
    assert sanitize("Example/Title: 123") == "ExampleTitle-123"
    assert sanitize("!@#$%^&*()[]{};':,.<>?/") == "!&"
    assert sanitize(None) is None


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
