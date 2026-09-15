__all__ = ["build_file", "evaluate_pattern", "from_comic_info", "from_metron_info"]

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from shortbox import Comic
from shortbox.metadata import ComicInfo, Metadata, MetronInfo
from shortbox.metadata.metron_info import Format

from perdoo.console import CONSOLE
from perdoo.settings import Naming
from perdoo.utils import SEPARATOR_CHARS, sanitize

FORMAT_SHORT_NAMES = {
    Format.ANNUAL: "Annual",
    Format.DIGITAL_CHAPTER: "Digital",
    Format.GRAPHIC_NOVEL: "GN",
    Format.HARDCOVER: "HC",
    Format.OMNIBUS: "OB",
    Format.TRADE_PAPERBACK: "TPB",
}
_COMIC_INFO_FORMAT_SHORT_NAMES = {fmt.value: short for fmt, short in FORMAT_SHORT_NAMES.items()}


class PatternSyntaxError(ValueError):
    pass


@dataclass(frozen=True)
class Placeholder:
    key: str
    padding: int | None


@dataclass(frozen=True)
class Group:
    children: Sequence["Node"]


Node = str | Placeholder | Group

_PLACEHOLDER_RE = re.compile(r"\{(?P<key>[a-zA-Z-]+)(?::(?P<padding>\d+))?\}")


def parse_pattern(pattern: str) -> list[Node]:  # noqa: C901
    pos = 0

    def parse_sequence(*, inside_group: bool) -> list[Node]:  # noqa: C901
        nonlocal pos
        nodes: list[Node] = []
        buffer: list[str] = []

        def flush_literal() -> None:
            if buffer:
                nodes.append("".join(buffer))
                buffer.clear()

        while pos < len(pattern):
            char = pattern[pos]
            if char == "\\" and pos + 1 < len(pattern) and pattern[pos + 1] in "{}[]\\":
                buffer.append(pattern[pos + 1])
                pos += 2
                continue
            if char == "]" and inside_group:
                flush_literal()
                return nodes
            if char == "{":
                match = _PLACEHOLDER_RE.match(pattern, pos)
                if not match:
                    raise PatternSyntaxError(
                        f"Malformed placeholder starting at position {pos} in {pattern!r}"
                    )
                flush_literal()
                padding = match.group("padding")
                nodes.append(
                    Placeholder(key=match.group("key"), padding=int(padding) if padding else None)
                )
                pos = match.end()
                continue
            if char == "[":
                flush_literal()
                pos += 1
                children = parse_sequence(inside_group=True)
                if pos >= len(pattern) or pattern[pos] != "]":
                    raise PatternSyntaxError(f"Unclosed '[' in naming pattern: {pattern!r}")
                pos += 1
                nodes.append(Group(children=children))
                continue
            buffer.append(char)
            pos += 1

        if inside_group:
            raise PatternSyntaxError(f"Unclosed '[' in naming pattern: {pattern!r}")
        flush_literal()
        return nodes

    return parse_sequence(inside_group=False)


def _resolve_placeholder(
    node: Placeholder,
    pattern_map: dict[str, Callable[[Metadata], str | int | None]],
    metadata: Metadata,
    seperator: Literal["-", "_", ".", " "],
) -> str:
    if node.key not in pattern_map:
        CONSOLE.print(f"Unknown naming pattern key: {node.key!r}", style="logging.level.warning")
        return ""

    value = pattern_map[node.key](metadata)
    if value is None:
        return ""

    if node.padding:
        match = re.fullmatch(r"(-?\d+)(\.\d+)?", str(value))
        if match:
            whole, fraction = match.groups()
            return f"{int(whole):0{node.padding}}{fraction or ''}"

    return sanitize(value=value, seperator=seperator) or ""


def _render(
    nodes: Sequence[Node],
    pattern_map: dict[str, Callable[[Metadata], str | int | None]],
    metadata: Metadata,
    seperator: Literal["-", "_", ".", " "],
) -> str:
    parts = []
    for node in nodes:
        if isinstance(node, str):
            parts.append(node)
        elif isinstance(node, Placeholder):
            parts.append(_resolve_placeholder(node, pattern_map, metadata, seperator))
        elif isinstance(node, Group):
            direct_placeholders = [
                child for child in node.children if isinstance(child, Placeholder)
            ]
            all_present = all(
                _resolve_placeholder(child, pattern_map, metadata, seperator)
                for child in direct_placeholders
            )
            if all_present:
                parts.append(_render(node.children, pattern_map, metadata, seperator))
    return "".join(parts)


def clean_path_string(value: str, seperator: str) -> str:
    value = re.sub(rf"[{re.escape(SEPARATOR_CHARS)}]{{2,}}", seperator, value)
    parts = [part.strip(SEPARATOR_CHARS) for part in value.split("/")]
    return "/".join(part for part in parts if part)


def evaluate_pattern(
    metadata: Metadata,
    pattern_map: dict[str, Callable[[Metadata], str | int | None]],
    pattern: str,
    seperator: Literal["-", "_", ".", " "],
) -> str:
    try:
        nodes = parse_pattern(pattern)
    except PatternSyntaxError as err:
        CONSOLE.print(
            f"{err}; using the pattern as a literal filename", style="logging.level.error"
        )
        return clean_path_string(pattern, seperator)

    rendered = _render(nodes, pattern_map, metadata, seperator)
    return clean_path_string(rendered, seperator)


def from_metron_info(metadata: MetronInfo, settings: Naming) -> str:
    pattern_map = {
        "cover-date": lambda x: str(x.cover_date) if x.cover_date else None,
        "cover-day": lambda x: x.cover_date.day if x.cover_date else None,
        "cover-month": lambda x: x.cover_date.month if x.cover_date else None,
        "cover-year": lambda x: x.cover_date.year if x.cover_date else None,
        "format": lambda x: x.series.format.value if x.series.format else None,
        "format-short": lambda x: (
            FORMAT_SHORT_NAMES.get(x.series.format) if x.series.format else None
        ),
        "id": lambda x: next((i.value for i in x.ids if i.primary), None),
        "imprint": lambda x: (
            x.publisher.imprint.value if x.publisher and x.publisher.imprint else None
        ),
        "isbn": lambda x: x.gtin.isbn if x.gtin else None,
        "issue-count": lambda x: x.series.issue_count,
        "lang": lambda x: x.series.lang,
        "number": lambda x: x.number,
        "publisher-id": lambda x: x.publisher.id if x.publisher else None,
        "publisher-name": lambda x: x.publisher.name if x.publisher else None,
        "series-id": lambda x: x.series.id,
        "series-name": lambda x: x.series.name,
        "series-sort-name": lambda x: x.series.sort_name,
        "series-year": lambda x: x.series.start_year,
        "store-date": lambda x: str(x.store_date) if x.store_date else None,
        "store-year": lambda x: x.store_date.year if x.store_date else None,
        "store-month": lambda x: x.store_date.month if x.store_date else None,
        "store-day": lambda x: x.store_date.day if x.store_date else None,
        "title": lambda x: x.collection_title,
        "upc": lambda x: x.gtin.upc if x.gtin else None,
        "volume": lambda x: x.series.volume if x.series.volume is not None else 1,
    }
    return evaluate_pattern(
        metadata=metadata,
        pattern_map=pattern_map,
        pattern=settings.pattern,
        seperator=settings.seperator,
    )


def from_comic_info(metadata: ComicInfo, settings: Naming) -> str:
    pattern_map = {
        "cover-date": lambda x: str(x.cover_date) if x.cover_date else None,
        "cover-day": lambda x: x.day,
        "cover-month": lambda x: x.month,
        "cover-year": lambda x: x.year,
        "format": lambda x: x.format,
        "format-short": lambda x: (
            _COMIC_INFO_FORMAT_SHORT_NAMES.get(x.format) if x.format else None
        ),
        "id": lambda _: None,
        "imprint": lambda x: x.imprint,
        "isbn": lambda _: None,
        "issue-count": lambda x: x.count,
        "lang": lambda x: x.language_iso,
        "number": lambda x: x.number,
        "publisher-id": lambda _: None,
        "publisher-name": lambda x: x.publisher,
        "series-id": lambda _: None,
        "series-name": lambda x: x.series,
        "series-sort-name": lambda _: None,
        "series-year": lambda x: x.volume if x.volume and x.volume >= 1900 else None,
        "store-date": lambda _: None,
        "store-day": lambda _: None,
        "store-month": lambda _: None,
        "store-year": lambda _: None,
        "title": lambda x: x.title,
        "upc": lambda _: None,
        "volume": lambda x: x.volume if x.volume and x.volume < 1900 else None,
    }
    return evaluate_pattern(
        metadata=metadata,
        pattern_map=pattern_map,
        pattern=settings.pattern,
        seperator=settings.seperator,
    )


_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_ILLEGAL_FS_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_MAX_COMPONENT_LENGTH = 150


def _make_component_safe(component: str) -> str:
    component = _ILLEGAL_FS_CHARS.sub("", component).strip(". ")
    if not component:
        return "_"
    if len(component) > _MAX_COMPONENT_LENGTH:
        component = component[:_MAX_COMPONENT_LENGTH].rstrip(". ") or "_"
    if component.upper() in _WINDOWS_RESERVED_NAMES:
        component = f"_{component}"
    return component


def enforce_filesystem_safety(relative_name: str) -> str:
    parts = [part for part in relative_name.split("/") if part]
    return "/".join(_make_component_safe(part) for part in parts)


def build_file(comic: Comic, folder: Path, settings: Naming) -> Path | None:
    if metron_info := comic.get_metadata(MetronInfo):
        filename = from_metron_info(metadata=metron_info, settings=settings)
    elif comic_info := comic.get_metadata(ComicInfo):
        filename = from_comic_info(metadata=comic_info, settings=settings)
    else:
        return None

    if not filename:
        CONSOLE.print(
            f"'{comic.file.name}' has no usable metadata for the naming pattern; keeping its current filename",  # noqa: E501
            style="logging.level.warning",
        )
        filename = comic.file.stem

    filename = enforce_filesystem_safety(filename)
    return (folder / (filename + comic.file.suffix)).resolve()
