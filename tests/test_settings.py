from pathlib import Path

import pytest

from perdoo.formats import ImageFormat
from perdoo.settings import Output, Settings


@pytest.fixture(autouse=True)
def _isolated_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("CONFIG", "DATA", "STATE", "CACHE"):
        monkeypatch.setenv(f"XDG_{name}_HOME", str(tmp_path / "xdg" / name.lower()))


def test_image_format_defaults_to_none() -> None:
    assert Output().image_format is None


def test_none_is_written_as_an_empty_string_and_read_back_as_none() -> None:
    settings = Settings().save()

    content = settings.path.read_text()
    loaded = Settings.load()

    assert 'image-format = ""' in content
    assert loaded.output.image_format is None


@pytest.mark.parametrize("value", ["jpg", "JPG", "Jpg"])
def test_image_format_is_read_case_insensitively(value: str) -> None:
    settings = Settings()
    settings.path.write_text(f'[output]\nimage-format = "{value}"\n')

    assert Settings.load().output.image_format is ImageFormat.JPG


def test_image_format_is_written_back_lowercase() -> None:
    settings = Settings()
    settings.path.write_text('[output]\nimage-format = "WEBP"\n')

    Settings.load().save()

    assert 'image-format = "webp"' in settings.path.read_text()
    assert Settings.load().output.image_format is ImageFormat.WEBP


def test_clearing_image_format_returns_it_to_none() -> None:
    settings = Settings()
    settings.path.write_text('[output]\nimage-format = "png"\n')
    loaded = Settings.load()
    loaded.output.image_format = None
    loaded.save()

    assert Settings.load().output.image_format is None


def test_invalid_image_format_names_the_setting() -> None:
    settings = Settings()
    settings.path.write_text('[output]\nimage-format = "gif"\n')

    with pytest.raises(ValueError, match=r"output\.image-format"):
        Settings.load()


def test_other_nullable_settings_read_an_empty_string_as_none() -> None:
    settings = Settings()
    settings.path.write_text('[services.comicvine]\napi-key = ""\n[services.metron]\ntoken = ""\n')

    loaded = Settings.load()

    assert loaded.services.comicvine.api_key is None
    assert loaded.services.metron.token is None


def test_non_nullable_empty_strings_are_left_alone() -> None:
    settings = Settings()
    settings.path.write_text('[output.naming]\npattern = ""\n')

    assert Settings.load().output.naming.pattern == ""


def test_nullable_settings_with_values_survive_a_round_trip() -> None:
    settings = Settings()
    settings.path.write_text('[services.comicvine]\napi-key = "abc"\n')

    Settings.load().save()

    assert Settings.load().services.comicvine.api_key == "abc"
