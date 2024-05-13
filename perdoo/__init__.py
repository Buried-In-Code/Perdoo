__all__ = [
    "__version__",
    "ARCHIVE_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "get_cache_dir",
    "get_config_dir",
    "get_data_dir",
    "setup_logging",
]
__version__ = "0.2.0"

import logging
import os
from pathlib import Path

from rich.logging import RichHandler
from rich.traceback import install

from perdoo.console import CONSOLE

ARCHIVE_EXTENSIONS = (".cb7", ".cbr", ".cbt", ".cbz")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def get_cache_dir() -> Path:
    cache_home = os.getenv("XDG_CACHE_HOME", default=str(Path.home() / ".cache"))
    folder = Path(cache_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_config_dir() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME", default=str(Path.home() / ".config"))
    folder = Path(config_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_data_dir() -> Path:
    data_home = os.getenv("XDG_DATA_HOME", default=str(Path.home() / ".local" / "share"))
    folder = Path(data_home).resolve() / "perdoo"
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_project_dir() -> Path:
    return Path(__file__).parent.parent


def setup_logging(debug: bool = False) -> None:
    install(show_locals=True, max_frames=6, console=CONSOLE)
    log_folder = get_project_dir() / "logs"
    log_folder.mkdir(parents=True, exist_ok=True)

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
    file_handler = logging.FileHandler(filename=log_folder / "perdoo.log")
    logging.basicConfig(
        format="[%(asctime)s] [%(levelname)-8s] {%(name)s} | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
        handlers=[console_handler, file_handler],
    )

    logging.getLogger("PIL").setLevel(logging.WARNING)
