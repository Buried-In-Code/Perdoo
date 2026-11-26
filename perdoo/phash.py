__all__ = ["hamming_distance", "phash"]

import cmath
import math
from collections.abc import Sequence
from functools import cache
from io import BytesIO
from typing import Final

from PIL import Image

_HASH_SIZE: Final[int] = 8
_IMAGE_SIZE: Final[int] = _HASH_SIZE * 4
_HEX_LENGTH: Final[int] = _HASH_SIZE * _HASH_SIZE // 4


@cache
def _twiddles(size: int) -> tuple[complex, ...]:
    return tuple(cmath.exp(-2j * math.pi * k / size) for k in range(size // 2))


@cache
def _dct_phases(size: int) -> tuple[complex, ...]:
    return tuple(cmath.exp(-1j * math.pi * k / (2 * size)) for k in range(size))


def _fft(values: Sequence[complex]) -> list[complex]:
    size = len(values)
    if size == 1:
        return list(values)
    even = _fft(values=values[0::2])
    odd = _fft(values=values[1::2])
    scaled = [twiddle * x for twiddle, x in zip(_twiddles(size=size), odd, strict=True)]
    return [a + b for a, b in zip(even, scaled, strict=True)] + [
        a - b for a, b in zip(even, scaled, strict=True)
    ]


def _dct(values: Sequence[float]) -> list[float]:
    size = len(values)
    ordered: list[complex] = [0j] * size
    for index, value in enumerate(values):
        ordered[index // 2 if index % 2 == 0 else size - 1 - index // 2] = complex(value)
    spectrum = _fft(values=ordered)
    return [2 * (phase * x).real for phase, x in zip(_dct_phases(size=size), spectrum, strict=True)]


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _compute_phash(image: Image.Image) -> str:
    pixels = image.convert("L").resize((_IMAGE_SIZE, _IMAGE_SIZE), Image.Resampling.LANCZOS)
    data = pixels.tobytes()
    rows = [data[y * _IMAGE_SIZE : (y + 1) * _IMAGE_SIZE] for y in range(_IMAGE_SIZE)]
    columns = [_dct(values=[row[x] for row in rows])[:_HASH_SIZE] for x in range(_IMAGE_SIZE)]
    block = [_dct(values=[column[y] for column in columns])[:_HASH_SIZE] for y in range(_HASH_SIZE)]
    values = [value for row in block for value in row]
    median = _median(values=values)
    bits = 0
    for value in values:
        bits = (bits << 1) | (value > median)
    return f"{bits:0{_HEX_LENGTH}x}"


def phash(image_bytes: bytes) -> str:
    with Image.open(BytesIO(image_bytes)) as img:
        return _compute_phash(image=img)


def hamming_distance(left: str, right: str) -> int:
    if len(left) != len(right):
        raise ValueError(f"hashes must be the same length, got {len(left)} and {len(right)}")
    return (int(left, 16) ^ int(right, 16)).bit_count()
