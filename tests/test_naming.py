from types import SimpleNamespace
from typing import Any

import pytest
from shortbox.metadata import ComicInfo, MetronInfo
from shortbox.metadata.metron_info import Format, Series

from perdoo.naming import (
    enforce_filesystem_safety,
    evaluate_pattern,
    from_comic_info,
    from_metron_info,
)
from perdoo.settings import Naming
from perdoo.utils import sanitize

PATTERN_MAP = {
    "publisher-name": lambda x: x.publisher,
    "series-name": lambda x: x.series,
    "volume": lambda x: x.volume,
    "format-short": lambda x: x.format_short,
    "number": lambda x: x.number,
}

DEFAULT_PATTERN = "{publisher-name}/{series-name}[-v{volume}]/{series-name}[-v{volume}][_{format-short}]_#{number:3}"  # noqa: E501


def meta(**kwargs: Any) -> SimpleNamespace:
    defaults = {
        "publisher": None,
        "series": None,
        "volume": None,
        "format_short": None,
        "number": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestSanitize:
    def test_none_returns_none(self) -> None:
        assert sanitize(None, "-") is None

    def test_all_punctuation_returns_none_not_empty_string(self) -> None:
        assert sanitize("???", "-") is None

    def test_preserves_decimal_issue_numbers(self) -> None:
        assert sanitize("1.5", "-") == "1.5"

    def test_does_not_glue_words_together(self) -> None:
        assert sanitize("Spider-Man", "_") == "Spider_Man"

    def test_preserves_unicode_letters(self) -> None:
        assert sanitize("Ëxtraño", "-") == "Ëxtraño"

    def test_uses_configured_separator(self) -> None:
        assert sanitize("Amazing Spider-Man", "_") == "Amazing_Spider_Man"


class TestEvaluatePattern:
    def test_full_metadata(self) -> None:
        m = meta(
            publisher="Marvel",
            series="Amazing Spider-Man",
            volume=5,
            format_short="TPB",
            number="7",
        )
        assert (
            evaluate_pattern(m, PATTERN_MAP, DEFAULT_PATTERN, "-")
            == "Marvel/Amazing-Spider-Man-v5/Amazing-Spider-Man-v5_TPB_#007"
        )

    def test_missing_format_short_leaves_no_double_underscore(self) -> None:
        m = meta(publisher="Marvel", series="Amazing Spider-Man", volume=5, number="7")
        result = evaluate_pattern(m, PATTERN_MAP, DEFAULT_PATTERN, "-")
        assert "__" not in result
        assert result == "Marvel/Amazing-Spider-Man-v5/Amazing-Spider-Man-v5_#007"

    def test_missing_volume_drops_whole_unit(self) -> None:
        m = meta(publisher="Marvel", series="Amazing Spider-Man", format_short="TPB", number="7")
        result = evaluate_pattern(m, PATTERN_MAP, DEFAULT_PATTERN, "-")
        assert "-v" not in result
        assert result == "Marvel/Amazing-Spider-Man/Amazing-Spider-Man_TPB_#007"

    def test_everything_missing_has_no_empty_path_components(self) -> None:
        m = meta(number=None)
        result = evaluate_pattern(m, PATTERN_MAP, DEFAULT_PATTERN, "-")
        assert "//" not in result
        assert not result.startswith("/")
        assert not result.endswith("/")

    def test_decimal_issue_number_pads_correctly(self) -> None:
        m = meta(publisher="Marvel", series="FCBD", number="1.5")
        result = evaluate_pattern(m, PATTERN_MAP, DEFAULT_PATTERN, "-")
        assert result.endswith("#001.5")

    def test_legacy_pattern_without_brackets_has_no_double_separator(self) -> None:
        legacy_pattern = "{series-name}_{format-short}_#{number:3}"
        m = meta(series="Amazing Spider-Man", number="7")
        result = evaluate_pattern(m, PATTERN_MAP, legacy_pattern, "-")
        assert "__" not in result

    def test_unknown_key_does_not_leak_into_filename(self) -> None:
        pattern = "{series-name}_{not-a-real-key}_#{number:3}"
        m = meta(series="Amazing Spider-Man", number="7")
        result = evaluate_pattern(m, PATTERN_MAP, pattern, "-")
        assert "not-a-real-key" not in result

    def test_malformed_pattern_does_not_raise(self) -> None:
        m = meta(series="Amazing Spider-Man")
        evaluate_pattern(m, PATTERN_MAP, "{series-name}[-v{volume}", "-")


class TestFormatShort:
    naming = Naming()

    @pytest.mark.parametrize("fmt", [Format.SINGLE_ISSUE, Format.LIMITED_SERIES, Format.ONE_SHOT])
    def test_unmapped_metron_format_is_omitted(self, fmt: Format) -> None:
        metadata = MetronInfo(
            series=Series(name="Amazing Spider-Man", volume=1, format=fmt), number="1"
        )
        result = from_metron_info(metadata, self.naming)
        assert result == "Amazing-Spider-Man-v1/Amazing-Spider-Man-v1_#001"

    def test_mapped_metron_format_still_shows(self) -> None:
        metadata = MetronInfo(
            series=Series(name="Amazing Spider-Man", volume=1, format=Format.TRADE_PAPERBACK),
            number="1",
        )
        result = from_metron_info(metadata, self.naming)
        assert result == "Amazing-Spider-Man-v1/Amazing-Spider-Man-v1_TPB_#001"

    def test_unmapped_comic_info_format_is_omitted(self) -> None:
        metadata = ComicInfo(
            series="Amazing Spider-Man", volume=1, format="Single Issue", number="1"
        )
        result = from_comic_info(metadata, self.naming)
        assert result == "Amazing-Spider-Man-v1/Amazing-Spider-Man-v1_#001"

    def test_mapped_comic_info_format_still_shows(self) -> None:
        metadata = ComicInfo(
            series="Amazing Spider-Man", volume=1, format="Trade Paperback", number="1"
        )
        result = from_comic_info(metadata, self.naming)
        assert result == "Amazing-Spider-Man-v1/Amazing-Spider-Man-v1_TPB_#001"


class TestEnforceFilesystemSafety:
    def test_escapes_windows_reserved_names(self) -> None:
        assert enforce_filesystem_safety("CON/CON") == "_CON/_CON"

    def test_strips_illegal_characters(self) -> None:
        assert enforce_filesystem_safety('Weird:Name?"') == "WeirdName"

    def test_truncates_overlong_components(self) -> None:
        assert len(enforce_filesystem_safety("A" * 300)) <= 150

    @pytest.mark.parametrize("value", ["...", "   ", "::"])
    def test_component_that_sanitizes_to_nothing_falls_back_to_placeholder(
        self, value: str
    ) -> None:
        assert enforce_filesystem_safety(value) == "_"
