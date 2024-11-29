__all__ = [
    "__version__",
    "get_cache_root",
    "get_config_root",
    "get_data_root",
    "get_state_root",
    "setup_logging",
]
__version__ = "0.4.0"

import logging
import os
from pathlib import Path

from rich.logging import RichHandler
from rich.traceback import install

from perdoo.console import CONSOLE


def get_cache_root() -> Path:
    cache_home = os.getenv("XDG_CACHE_HOME", default=str(Path.home() / ".cache"))
    folder = Path(cache_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_config_root() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME", default=str(Path.home() / ".config"))
    folder = Path(config_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_data_root() -> Path:
    data_home = os.getenv("XDG_DATA_HOME", default=str(Path.home() / ".local" / "share"))
    folder = Path(data_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_state_root() -> Path:
    data_home = os.getenv("XDG_STATE_HOME", default=str(Path.home() / ".local" / "state"))
    folder = Path(data_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def setup_logging(debug: bool = False) -> None:
    install(show_locals=True, max_frames=6, console=CONSOLE)

    console_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        omit_repeated_times=False,
        show_level=True,
        show_time=False,
        show_path=False,
        console=CONSOLE,
    )
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    file_handler = logging.FileHandler(filename=get_state_root() / "perdoo.log")
    file_handler.setLevel(logging.DEBUG)
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)-8s] {%(name)s} | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
        handlers=[console_handler, file_handler],
    )

    logging.getLogger("PIL").setLevel(logging.WARNING)
