__all__ = ["CONSOLE"]

import logging

from rich.console import Console
from rich.theme import Theme

LOGGER = logging.getLogger(__name__)

CONSOLE = Console(
    theme=Theme(
        {
            "prompt": "cyan",
            "prompt.border": "dim bright_cyan",
            "prompt.choices": "white",
            "prompt.default": "italic white",
            "title": "bold not dim blue",
            "subtitle": "not dim blue",
            "logging.level.debug": "dim white",
            "logging.level.info": "white",
            "logging.level.warning": "yellow",
            "logging.level.error": "red",
            "logging.level.critical": "bold bright_red",
        }
    )
)
