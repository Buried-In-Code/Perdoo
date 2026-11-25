__all__ = ["__version__", "get_cache_home", "get_config_home", "get_data_home", "get_state_home"]
__version__ = "1.5.0"
__project__ = "perdoo"

import os
from pathlib import Path


def get_cache_home() -> Path:
    cache_home = os.getenv("XDG_CACHE_HOME", default=str(Path.home() / ".cache"))
    folder = Path(cache_home).resolve() / __project__
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_config_home() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME", default=str(Path.home() / ".config"))
    folder = Path(config_home).resolve() / __project__
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_data_home() -> Path:
    data_home = os.getenv("XDG_DATA_HOME", default=str(Path.home() / ".local" / "share"))
    folder = Path(data_home).resolve() / __project__
    folder.mkdir(exist_ok=True, parents=True)
    return folder


def get_state_home() -> Path:
    data_home = os.getenv("XDG_STATE_HOME", default=str(Path.home() / ".local" / "state"))
    folder = Path(data_home).resolve() / __project__
    folder.mkdir(exist_ok=True, parents=True)
    return folder
