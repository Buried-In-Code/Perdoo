__all__ = ["CONSOLE", "create_menu"]

import logging

from rich.console import Console
from rich.panel import Panel
from rich.prompt import IntPrompt
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


def create_menu(
    options: list[str],
    title: str | None = None,
    subtitle: str | None = None,
    prompt: str = "Select",
    default: str | None = None,
) -> int | None:
    if not options:
        return 0
    panel_text = []
    padding = len(str(len(options)))
    for index, item in enumerate(options):
        panel_text.append(
            f"[markdown.item.number]{index + 1:>{padding}}.[/] [prompt.choices]{item}[/]"
        )
    if default:
        panel_text.append(f"[markdown.item.number]{0:>{padding}}.[/] [prompt.default]{default}[/]")
    CONSOLE.print(
        Panel(
            "\n".join(panel_text),
            title=f"[title]{title}[/]" if title else None,
            subtitle=f"[subtitle]{subtitle}[/]" if subtitle else None,
            border_style="prompt.border",
        )
    )
    selected = IntPrompt.ask(prompt=prompt, default=0 if default else None, console=CONSOLE)
    if (
        selected is None
        or selected < 0
        or selected > len(options)
        or (selected == 0 and not default)
    ):
        LOGGER.warning("Invalid Option: %s", selected)
        return create_menu(
            options=options, title=title, subtitle=subtitle, prompt=prompt, default=default
        )
    return selected
