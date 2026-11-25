from pathlib import PurePosixPath, PureWindowsPath

import pytest

from perdoo.utils import flatten_dict, is_same_path, sanitize


@pytest.mark.parametrize(
    ("value", "seperator", "expected"),
    [
        ("  Spider-Man: No Way Home!  ", "-", "Spider-Man-No-Way-Home!"),
        ("A/B & C", "_", "AB_&_C"),
        (42, ".", "42"),
        (None, " ", None),
    ],
    ids=[
        "normalizes-punctuation",
        "preserves-allowed-characters",
        "coerces-integer",
        "preserves-none",
    ],
)
def test_sanitize_normalizes_values(
    value: str | int | None, seperator: str, expected: str | None
) -> None:
    assert sanitize(value, seperator) == expected


def test_flatten_dict_flattens_nested_mappings_and_mapping_lists() -> None:
    content = {
        "series": {"name": "Spider-Man", "issues": [{"number": 2}, {"number": 10}]},
        "tags": ["Marvel", "Comics"],
    }

    assert flatten_dict(content) == {
        "series.issues[0].number": 2,
        "series.issues[1].number": 10,
        "series.name": "Spider-Man",
        "tags": ["Marvel", "Comics"],
    }


@pytest.mark.parametrize("path_type", [PurePosixPath, PureWindowsPath])
def test_is_same_path_matches_identical_paths(path_type: type[PurePosixPath]) -> None:
    assert is_same_path(path_type("lib/Series/a.cbz"), path_type("lib/Series/a.cbz"))


@pytest.mark.parametrize("path_type", [PurePosixPath, PureWindowsPath])
@pytest.mark.parametrize("other", ["lib/Series/a.CBZ", "lib/Series/A.cbz", "lib/Series/b.cbz"])
def test_is_same_path_tells_apart_names_that_differ_in_case(
    path_type: type[PurePosixPath], other: str
) -> None:
    assert not is_same_path(path_type("lib/Series/a.cbz"), path_type(other))


@pytest.mark.parametrize("path_type", [PurePosixPath, PureWindowsPath])
def test_is_same_path_tells_apart_folders(path_type: type[PurePosixPath]) -> None:
    assert not is_same_path(path_type("lib/one/a.cbz"), path_type("lib/two/a.cbz"))


def test_windows_paths_hide_case_only_differences_without_is_same_path() -> None:
    left, right = PureWindowsPath("lib/a.CBZ"), PureWindowsPath("lib/a.cbz")

    assert left == right
    assert not is_same_path(left, right)
