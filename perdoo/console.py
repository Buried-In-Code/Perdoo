__all__ = ["CONSOLE", "Grid"]

from rich.box import Box
from rich.console import Console
from rich.table import PaddingDimensions, Table
from rich.text import Text
from rich.theme import Theme

CONSOLE = Console(
    theme=Theme(
        {
            "logging.level.debug": "dim white",
            "logging.level.info": "white",
            "logging.level.warning": "yellow",
            "logging.level.error": "red",
            "logging.level.critical": "bold bright_red",
        }
    )
)


class Grid(Table):
    def __init__(
        self,
        title: str | Text | None = None,
        box: Box | None = None,
        padding: PaddingDimensions = (0, 2),
        show_header: bool = False,
        show_edge: bool | None = None,
    ):
        super().__init__(
            title=title,
            box=box or Box(" ── \n    \n    \n    \n    \n    \n    \n    \n"),
            padding=padding,
            show_header=show_header,
            show_edge=title is not None if show_edge is None else show_edge,
        )
