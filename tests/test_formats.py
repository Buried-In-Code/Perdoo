from importlib.util import find_spec

import pytest
from msgspec import ValidationError
from msgspec.toml import decode
from shortbox import archives
from shortbox.archives import TarArchive, ZipArchive

from perdoo.formats import ArchiveFormat, ArchiveType, ImageFormat, standardize_image_suffix
from perdoo.settings import Output


@pytest.mark.parametrize("enum_type", [ArchiveType, ArchiveFormat, ImageFormat])
def test_members_are_lowercase_extensions(enum_type: type[ArchiveType]) -> None:
    for member in enum_type:
        assert member.extension == f".{member.value}"
        assert str(member) == member.value


@pytest.mark.parametrize("value", ["cbz", "CBZ", "Cbz"])
def test_lookup_is_case_insensitive(value: str) -> None:
    assert ArchiveType(value) is ArchiveType.CBZ
    assert ArchiveFormat(value) is ArchiveFormat.CBZ


def test_lookup_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="is not a valid ArchiveType"):
        ArchiveType("zip")


def test_archive_format_is_only_what_can_be_written() -> None:
    assert {x.value for x in ArchiveFormat} <= {x.value for x in ArchiveType}
    assert not {"cbr", "pdf"} & {x.value for x in ArchiveFormat}


def test_archive_format_resolves_shortbox_classes() -> None:
    assert ArchiveFormat.CBZ.archive_class is ZipArchive
    assert ArchiveFormat.CBT.archive_class is TarArchive


@pytest.mark.skipif(find_spec("py7zr") is None, reason="requires perdoo[cb7]")
def test_archive_format_resolves_cb7_when_installed() -> None:
    assert ArchiveFormat.CB7.archive_class.__name__ == "SevenZipArchive"


def test_archive_format_names_the_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(archives, "SevenZipArchive", raising=False)

    with pytest.raises(ImportError, match=r"perdoo\[cb7\]"):
        _ = ArchiveFormat.CB7.archive_class


@pytest.mark.parametrize(
    ("format_", "extension", "pillow"),
    [
        (ImageFormat.JPG, ".jpg", "JPEG"),
        (ImageFormat.PNG, ".png", "PNG"),
        (ImageFormat.WEBP, ".webp", "WEBP"),
        (ImageFormat.JXL, ".jxl", "JXL"),
    ],
)
def test_image_format_properties(format_: ImageFormat, extension: str, pillow: str) -> None:
    assert format_.extension == extension
    assert format_.pillow_format == pillow


def test_output_settings_decode_archive_format() -> None:
    output = decode(b'archive-format = "cb7"', type=Output)

    assert output.archive_format is ArchiveFormat.CB7


def test_output_settings_default_archive_format() -> None:
    assert Output().archive_format is ArchiveFormat.CBZ


@pytest.mark.parametrize("value", ["cbr", "pdf", "zip"])
def test_output_settings_reject_formats_that_cannot_be_written(value: str) -> None:
    with pytest.raises(ValidationError, match="Invalid enum value"):
        decode(f'archive-format = "{value}"'.encode(), type=Output)


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        (".jpeg", ".jpg"),
        (".JPEG", ".jpg"),
        (".JPG", ".jpg"),
        (".jpg", ".jpg"),
        (".PNG", ".png"),
        (".WebP", ".webp"),
        (".jxl", ".jxl"),
    ],
)
def test_standardize_image_suffix(suffix: str, expected: str) -> None:
    assert standardize_image_suffix(suffix) == expected
