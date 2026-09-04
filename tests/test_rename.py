from perdoo.cli.rename import evaluate_pattern


def test_evaluate_pattern_sanitizes_values_pads_numbers_and_strips_leading_slash() -> None:
    result = evaluate_pattern(
        metadata=object(),
        pattern_map={"series-name": lambda _: "Spider-Man", "number": lambda _: "7"},
        pattern="/{series-name}/#{number:3}",
        seperator="-",
    )

    assert result == "Spider-Man/#007"


def test_evaluate_pattern_replaces_missing_values_with_an_empty_string() -> None:
    result = evaluate_pattern(
        metadata=object(), pattern_map={"title": lambda _: None}, pattern="{title}", seperator="_"
    )

    assert result == ""
