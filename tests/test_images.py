import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from perdoo.cli.convert.image import convert_comic_images
from PIL import Image, ImageChops, ImageCms
from shortbox import Comic
from shortbox.archives import Archive, TarArchive, ZipArchive

from perdoo.cli._runner import Outcome
from perdoo.formats import ImageFormat
from perdoo.images import convert_image

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".jxl")
LOSSLESS = [ImageFormat.PNG, ImageFormat.WEBP, ImageFormat.JXL]


def _encode(image: Image.Image, format_: str, **options: object) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=format_, **options)
    return buffer.getvalue()


def _pattern(size: tuple[int, int] = (64, 32), mode: str = "RGB") -> Image.Image:
    bands = len(mode)
    data = bytes(i * 37 % 256 for i in range(size[0] * size[1] * bands))
    return Image.frombytes(mode, size, data)


def _png(mode: str = "RGB") -> bytes:
    return _encode(_pattern(mode=mode), "PNG")


def _load(data: bytes) -> Image.Image:
    image = Image.open(BytesIO(data))
    image.load()
    return image


def _same_pixels(left: Image.Image, right: Image.Image) -> bool:
    return ImageChops.difference(left.convert("RGB"), right.convert("RGB")).getbbox() is None


@pytest.mark.parametrize("target", list(ImageFormat))
def test_convert_image_produces_target_format(target: ImageFormat) -> None:
    assert _load(convert_image(data=_png(), target=target)).format == target.pillow_format


@pytest.mark.parametrize("target", LOSSLESS)
def test_lossless_targets_keep_every_pixel(target: ImageFormat) -> None:
    converted = convert_image(data=_png(), target=target)

    assert _same_pixels(_load(converted), _pattern())


def test_jpg_target_is_lossy() -> None:
    converted = convert_image(data=_png(), target=ImageFormat.JPG)

    assert not _same_pixels(_load(converted), _pattern())


@pytest.mark.parametrize("mode", ["1", "L", "LA", "P", "RGB", "RGBA"])
@pytest.mark.parametrize("target", list(ImageFormat))
def test_convert_image_handles_png_modes(mode: str, target: ImageFormat) -> None:
    source = _pattern(mode="RGB" if mode == "P" else mode).convert(mode)

    converted = convert_image(data=_encode(source, "PNG"), target=target)

    assert _load(converted).size == source.size


@pytest.mark.parametrize("target", list(ImageFormat))
def test_sixteen_bit_grayscale_is_not_blown_out(target: ImageFormat) -> None:
    source = Image.new("I;16", (8, 8), 40000)

    converted = _load(convert_image(data=_encode(source, "PNG"), target=target))

    if converted.mode == "I;16":
        brightness = converted.getpixel((2, 2)) / 65535
    else:
        brightness = converted.convert("L").getpixel((2, 2)) / 255
    assert brightness == pytest.approx(40000 / 65535, abs=0.01)


def test_jpg_target_flattens_transparency_onto_white() -> None:
    source = Image.new("RGBA", (8, 8), (255, 0, 0, 0))

    converted = _load(convert_image(data=_encode(source, "PNG"), target=ImageFormat.JPG))

    assert converted.mode == "RGB"
    assert min(converted.getpixel((2, 2))) >= 250


def test_jpg_target_flattens_palette_transparency() -> None:
    source = Image.new("P", (8, 8), 0)
    source.putpalette([255, 0, 0] * 256)

    converted = _load(
        convert_image(data=_encode(source, "PNG", transparency=0), target=ImageFormat.JPG)
    )

    assert min(converted.getpixel((2, 2))) >= 250


def test_jpg_target_keeps_grayscale() -> None:
    assert _load(convert_image(data=_png(mode="L"), target=ImageFormat.JPG)).mode == "L"


@pytest.mark.parametrize("target", list(ImageFormat))
def test_exif_is_preserved(target: ImageFormat) -> None:
    exif = Image.Exif()
    exif[0x010E] = "page note"
    data = _encode(_pattern(), "PNG", exif=exif.tobytes())

    assert _load(convert_image(data=data, target=target)).getexif().get(0x010E) == "page note"


@pytest.mark.parametrize("target", [ImageFormat.JPG, ImageFormat.PNG, ImageFormat.WEBP])
def test_icc_profile_is_preserved(target: ImageFormat) -> None:
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
    data = _encode(_pattern(), "PNG", icc_profile=profile)

    assert _load(convert_image(data=data, target=target)).info.get("icc_profile") == profile


def test_jpeg_to_jxl_is_a_lossless_transcode() -> None:
    jpeg = _encode(_pattern((256, 256)), "JPEG", quality=85)

    converted = convert_image(data=jpeg, target=ImageFormat.JXL)

    assert len(converted) < len(jpeg)
    assert _same_pixels(_load(converted), _load(jpeg))


def test_cmyk_jpeg_to_jxl_falls_back_to_pixel_conversion() -> None:
    jpeg = _encode(_pattern(mode="CMYK"), "JPEG")

    assert _load(convert_image(data=jpeg, target=ImageFormat.JXL)).format == "JXL"


def test_convert_image_rejects_non_images() -> None:
    with pytest.raises(OSError, match="cannot identify image file"):
        convert_image(data=b"not an image", target=ImageFormat.PNG)


def _make_archive(
    archive_type: type[Archive], folder: Path, files: dict[str, bytes], name: str = "comic"
) -> Path:
    paths = []
    for filename, data in files.items():
        path = folder / "src" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        paths.append(path)
    return archive_type.archive_files(parent=folder, name=name, files=paths)


def _convert(file: Path, target: ImageFormat) -> tuple[Outcome, list[str]]:
    with Comic.open(file=file) as comic:
        outcome = convert_comic_images(
            comic=comic, target=target, image_extensions=IMAGE_EXTENSIONS
        )
    with Comic.open(file=file) as comic:
        return outcome, comic.list_filenames()


@pytest.mark.parametrize("archive_type", [ZipArchive, TarArchive], ids=["cbz", "cbt"])
def test_convert_comic_images_replaces_pages(archive_type: type[Archive], tmp_path: Path) -> None:
    file = _make_archive(
        archive_type,
        tmp_path,
        {"page1.png": _png(), "page2.jpeg": _encode(_pattern(), "JPEG"), "ComicInfo.xml": b"<x/>"},
    )

    outcome, names = _convert(file, ImageFormat.WEBP)

    assert outcome is Outcome.SUCCESS
    assert names == ["ComicInfo.xml", "page1.webp", "page2.webp"]


def test_convert_comic_images_is_unchanged_for_target_format(tmp_path: Path) -> None:
    file = _make_archive(ZipArchive, tmp_path, {"page1.png": _png()})

    outcome, names = _convert(file, ImageFormat.PNG)

    assert outcome is Outcome.UNCHANGED
    assert names == ["page1.png"]


@pytest.mark.parametrize("name", ["page1.jpeg", "page1.JPG", "page1.JPEG", "page1.Jpg"])
def test_convert_comic_images_standardizes_jpg_without_reencoding(
    name: str, tmp_path: Path
) -> None:
    jpeg = _encode(_pattern(), "JPEG")
    file = _make_archive(ZipArchive, tmp_path, {name: jpeg})

    outcome, names = _convert(file, ImageFormat.JPG)

    assert outcome is Outcome.SUCCESS
    assert names == ["page1.jpg"]
    with Comic.open(file=file) as comic:
        assert comic.read_file(filename="page1.jpg") == jpeg


def test_convert_comic_images_standardizes_other_formats_too(tmp_path: Path) -> None:
    file = _make_archive(ZipArchive, tmp_path, {"page1.PNG": _png()})

    outcome, names = _convert(file, ImageFormat.PNG)

    assert outcome is Outcome.SUCCESS
    assert names == ["page1.png"]


def test_convert_comic_images_dry_run_changes_nothing(tmp_path: Path) -> None:
    file = _make_archive(
        ZipArchive, tmp_path, {"a.png": _png(), "b.JPEG": _encode(_pattern(), "JPEG")}
    )
    before = file.read_bytes()

    with Comic.open(file=file) as comic:
        outcome = convert_comic_images(
            comic=comic, target=ImageFormat.JPG, image_extensions=IMAGE_EXTENSIONS, dry_run=True
        )

    assert outcome is Outcome.SUCCESS
    assert file.read_bytes() == before


def test_convert_comic_images_dry_run_logs_in_debug_style(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    file = _make_archive(ZipArchive, tmp_path, {"a.png": _png(), "b.JPEG": b"x"})

    with Comic.open(file=file) as comic:
        convert_comic_images(
            comic=comic, target=ImageFormat.JPG, image_extensions=IMAGE_EXTENSIONS, dry_run=True
        )

    output = capsys.readouterr().out
    assert "Would convert 'a.png' to 'a.jpg'" in output
    assert "Would rename 'b.JPEG' to 'b.jpg'" in output


def test_convert_comic_images_matches_extensions_case_insensitively(tmp_path: Path) -> None:
    file = _make_archive(ZipArchive, tmp_path, {"PAGE.PNG": _png()})

    _, names = _convert(file, ImageFormat.JPG)

    assert names == ["PAGE.jpg"]


def test_convert_comic_images_keeps_subfolders(tmp_path: Path) -> None:
    file = tmp_path / "comic.cbz"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("chapter 1/001.png", _png())

    _, names = _convert(file, ImageFormat.JPG)

    assert names == ["chapter 1/001.jpg"]


def test_convert_comic_images_never_overwrites_an_existing_page(tmp_path: Path) -> None:
    other = _encode(_pattern(mode="L"), "JPEG")
    file = _make_archive(ZipArchive, tmp_path, {"page.png": _png(), "page.jpg": other})

    outcome, names = _convert(file, ImageFormat.JPG)

    assert outcome is Outcome.FAILED
    assert names == ["page.jpg", "page.png"]
    with Comic.open(file=file) as comic:
        assert comic.read_file(filename="page.jpg") == other


def test_convert_comic_images_reports_corrupt_pages_but_converts_the_rest(tmp_path: Path) -> None:
    file = _make_archive(ZipArchive, tmp_path, {"a.png": b"corrupt", "b.png": _png()})

    outcome, names = _convert(file, ImageFormat.JPG)

    assert outcome is Outcome.FAILED
    assert names == ["a.png", "b.jpg"]
