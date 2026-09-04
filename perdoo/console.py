__all__ = ["CONSOLE"]

from rich.console import Console
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
