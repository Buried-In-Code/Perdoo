__all__ = ["Service", "prompt_select"]

from typing import Any, Protocol

from prompt_toolkit.styles import Style
from questionary import Choice, select

from perdoo.services._models import MetadataResult, Search

DEFAULT_CHOICE = Choice(title="None of the Above", value=None)


def prompt_select(message: str, choices: list[Choice]) -> Any:  # noqa: ANN401
    if not choices:
        return None
    selected = select(
        message,
        default=DEFAULT_CHOICE,
        choices=[*choices, DEFAULT_CHOICE],
        style=Style([("dim", "dim")]),
    ).ask()
    if select and selected != DEFAULT_CHOICE.title:
        return selected
    return None


class Service(Protocol):
    def fetch(self, search: Search) -> MetadataResult | None: ...
