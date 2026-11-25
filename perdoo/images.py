__all__ = ["convert_image"]

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pillow_jxl  # noqa: F401
from PIL import Image
from PIL.Image import Image as PILImage

from perdoo.formats import ImageFormat

_NATIVE_MODES: dict[ImageFormat, frozenset[str]] = {
    ImageFormat.JPG: frozenset({"1", "L", "RGB", "CMYK"}),
    ImageFormat.PNG: frozenset({"1", "L", "LA", "I;16", "P", "RGB", "RGBA"}),
    ImageFormat.WEBP: frozenset({"RGB", "RGBA"}),
    ImageFormat.JXL: frozenset({"L", "LA", "I;16", "RGB", "RGBA"}),
}
_SAVE_OPTIONS: dict[ImageFormat, dict[str, object]] = {
    ImageFormat.JPG: {"quality": 95},
    ImageFormat.WEBP: {"lossless": True},
    ImageFormat.JXL: {"lossless": True},
}
_TRANSCODABLE_JPEG_MODES = frozenset({"L", "RGB"})


def _flatten_on_white(image: PILImage) -> PILImage:
    rgba = image.convert("RGBA")
    return Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")


def _prepare(image: PILImage, target: ImageFormat) -> PILImage:
    native = _NATIVE_MODES[target]
    if image.mode == "I;16" and image.mode not in native:
        image = image.point(lambda value: value / 256).convert("L")
    if target is ImageFormat.JPG and image.has_transparency_data:
        return _flatten_on_white(image=image)
    if image.mode in native:
        return image
    return image.convert("RGBA" if image.has_transparency_data else "RGB")


def _transcode_jpeg_to_jxl(data: bytes) -> bytes:
    with TemporaryDirectory() as folder:
        file = Path(folder) / "page.jpg"
        file.write_bytes(data)
        with Image.open(file) as image:
            buffer = BytesIO()
            image.save(buffer, format=ImageFormat.JXL.pillow_format, lossless_jpeg=True)
    return buffer.getvalue()


def convert_image(data: bytes, target: ImageFormat) -> bytes:
    with Image.open(BytesIO(data)) as image:
        if (
            target is ImageFormat.JXL
            and image.format == "JPEG"
            and image.mode in _TRANSCODABLE_JPEG_MODES
        ):
            return _transcode_jpeg_to_jxl(data=data)
        image.load()
        options = dict(_SAVE_OPTIONS.get(target, {}))
        for key in ("exif", "icc_profile"):
            if value := image.info.get(key):
                options[key] = value
        buffer = BytesIO()
        _prepare(image=image, target=target).save(buffer, format=target.pillow_format, **options)
    return buffer.getvalue()
