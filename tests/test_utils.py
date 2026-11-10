import pytest

from perdoo.utils import flatten_dict, sanitize


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


def test_existing_file_missing_path_reports_missing(tmp_path) -> None:
    from argparse import ArgumentTypeError

    from perdoo.cli._utils import existing_file

    with pytest.raises(ArgumentTypeError, match="must exist"):
        existing_file(str(tmp_path / "nope.cbz"))


def test_existing_file_directory_reports_not_a_file(tmp_path) -> None:
    from argparse import ArgumentTypeError

    from perdoo.cli._utils import existing_file

    with pytest.raises(ArgumentTypeError, match="not a file"):
        existing_file(str(tmp_path))


def test_existing_file_returns_path_for_file(tmp_path) -> None:
    from perdoo.cli._utils import existing_file

    target = tmp_path / "issue.cbz"
    target.write_bytes(b"fake")
    assert existing_file(str(target)) == target.resolve()


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
