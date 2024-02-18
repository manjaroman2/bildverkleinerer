from pathlib import Path
from sys import platform


def _get_datadir() -> Path:
    """
    Returns a parent directory path
    where persistent application data can be stored.

    # linux: ~/.local/share
    # macOS: ~/Library/Application Support
    # windows: C:/Users/<USER>/AppData/Roaming
    """

    home = Path.home()

    if platform == "win32":
        return home / "AppData/Roaming"
    elif platform.startswith("linux"):
        return home / ".local/share"
    elif platform == "darwin":
        return home / "Library/Application Support"


def get_datadir(_str: str) -> Path:
    datadir = _get_datadir() / _str
    try:
        datadir.mkdir(parents=True)
    except FileExistsError:
        pass
    return datadir
