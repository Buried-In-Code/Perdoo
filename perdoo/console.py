__all__ = ["CONSOLE", "Grid"]

from rich.box import Box
from rich.console import Console
from rich.table import PaddingDimensions, Table
from rich.text import Text
from rich.theme import Theme

CONSOLE = Console(
    theme=Theme(
        {
            "title": "#4682B4",
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
        show_edge: bool = False,
    ):
        super().__init__(
            title=title, box=box, padding=padding, show_header=show_header, show_edge=show_edge
        )
