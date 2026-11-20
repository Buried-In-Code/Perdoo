__all__ = ["Prompts"]

from collections.abc import Sequence
from typing import Any

from prompt_toolkit.styles import Style
from questionary import Choice, confirm, select, text
from shortbox.metadata.metron_info import Format

from perdoo.services._provider import Candidate

_NONE_OF_THE_ABOVE = Choice(title="None of the Above", value=None)
_STYLE = Style([("dim", "dim")])


def _select(message: str, choices: list[Choice]) -> Any:  # noqa: ANN401
    result = select(
        message, default=_NONE_OF_THE_ABOVE, choices=[*choices, _NONE_OF_THE_ABOVE], style=_STYLE
    ).ask()
    if result and result != _NONE_OF_THE_ABOVE.title:
        return result
    return None


class Prompts:
    def select(self, message: str, candidates: Sequence[Candidate]) -> Candidate | None:
        choices = [
            Choice(
                title=[
                    ("class:dim", f"{x.id} | {x.detail + ' | ' if x.detail else ''}"),
                    ("class:title", x.title),
                ],
                description=x.url,
                value=x,
            )
            for x in candidates
        ]
        return _select(message, choices) if choices else None

    def select_format(self) -> Format | None:
        return _select("Select a format", [Choice(title=str(x), value=x) for x in Format])

    def confirm(self, message: str) -> bool:
        return bool(confirm(message, default=False).ask())

    def text(self, message: str) -> str | None:
        return (text(message).ask() or "").strip() or None
