__all__ = ["Outcome", "RunSummary", "collect_files", "run_on_files"]

from argparse import Namespace
from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from shortbox.errors import ArchiveCapabilityError, UnsupportedArchiveError

from perdoo.console import CONSOLE, Grid
from perdoo.utils import list_files


class Outcome(StrEnum):
    SUCCESS = "Success"
    UNCHANGED = "Unchanged"
    SKIPPED = "Skipped"
    FAILED = "Failed"


@dataclass
class RunSummary:
    counts: Counter[Outcome] = field(default_factory=Counter)

    def record(self, outcome: Outcome) -> None:
        self.counts[outcome] += 1

    def __rich__(self) -> Table:
        table = Grid(title="Summary")
        for outcome in Outcome:
            table.add_row(
                outcome.value,
                str(self.counts[outcome]),
                style="logging.level.debug"
                if self.counts[outcome] == 0
                else "logging.level.error"
                if outcome is Outcome.FAILED
                else "logging.level.info",
            )
        return table


def collect_files(args: Namespace) -> list[Path]:
    files = list_files(args.target) if args.target.is_dir() else [args.target]
    ignored = {f".{x}" for x in args.ignore or ()}
    return [x for x in files if x.suffix not in ignored]


def run_on_files(
    files: Sequence[Path],
    action: str,
    handler: Callable[[Path], Outcome],
    *,
    show_progress: bool = True,
    capability_hint: str | None = "Consider converting to another format first",
) -> RunSummary:
    summary = RunSummary()
    progress = (
        Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=CONSOLE,
            expand=True,
            transient=True,
        )
        if show_progress
        else None
    )
    with progress or nullcontext():
        entries = progress.track(files, description=f"{action} comics") if progress else files
        for entry in entries:
            try:
                summary.record(outcome=handler(entry))
            except UnsupportedArchiveError:
                summary.record(outcome=Outcome.SKIPPED)
            except ArchiveCapabilityError as err:
                hint = f": {capability_hint}" if capability_hint else ""
                CONSOLE.print(f"{err}{hint}", style="logging.level.warning")
                summary.record(outcome=Outcome.FAILED)
            except Exception as err:  # noqa: BLE001
                CONSOLE.print(
                    f"{action} failed for '{entry.name}': {err}", style="logging.level.error"
                )
                summary.record(outcome=Outcome.FAILED)
    CONSOLE.print(summary, style="logging.level.info")
    return summary
