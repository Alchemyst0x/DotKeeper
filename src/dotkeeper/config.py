from importlib.metadata import version
from pathlib import Path

import platformdirs
import yaml

APP_NAME = 'DotKeeper'
APP_AUTHOR = 'Alchemyst0x'
APP_VERSION = version('dotkeeper')

DEFAULT_CONFIG = {
    '$HOME/.bashrc': '$HOME/dotfiles/.bashrc',
    '$HOME/.zshrc': '$HOME/dotfiles/.zshrc',
    '$HOME/.config/nvim': '$HOME/dotfiles/nvim',
    '$HOME/.config/alacritty': '$HOME/dotfiles/alacritty',
    '$HOME/.gitconfig': '$HOME/dotfiles/.gitconfig',
    '$HOME/.tmux.conf': '$HOME/dotfiles/.tmux.conf',
}


def get_config_dir() -> Path:
    """Get the configuration directory for DotKeeper.

    Returns
    -------
    Path
        Path to the configuration directory
    """

    return Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR, version=APP_VERSION))


def get_data_dir() -> Path:
    """Get the data directory for DotKeeper.

    Returns
    -------
    Path
        Path to the data directory
    """

    return Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR, version=APP_VERSION))


def get_cache_dir() -> Path:
    """Get the cache directory for DotKeeper.

    Returns
    -------
    Path
        Path to the cache directory
    """

    return Path(platformdirs.user_cache_dir(APP_NAME, APP_AUTHOR, version=APP_VERSION))


def get_working_dir_config() -> Path | None:
    """Check for config file in current working directory.

    Returns
    -------
    Path | None
        Path to config file if found in working directory, None otherwise
    """

    cwd = Path.cwd()
    for name in ['config.yml', 'dotkeeper.yml', '.dotkeeper.yml']:
        if (config_file := cwd / name).is_file():
            return config_file
    return None


def ensure_config_exists() -> Path:
    """Ensure the config file exists, creating it if necessary.

    Returns
    -------
    Path
        Path to the config file
    """

    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / 'config.yml'
    if not config_file.exists():
        with config_file.open('w') as f:
            yaml.safe_dump(DEFAULT_CONFIG, f, sort_keys=False)

    return config_file


def get_default_config_paths() -> list[Path]:
    """Get the default configuration file paths.

    Returns
    -------
    list[Path]
        List of possible config file paths in order of precedence
    """

    xdg_config = Path.home() / '.config' / 'dotkeeper' / 'config.yml'
    platform_config = get_config_dir() / 'config.yml'

    # Order of precedence:
    # 1. Environment variable (handled in cli.py)
    # 2. Working directory config files
    # 3. XDG config directory
    # 4. Platform-specific config directory
    return [
        *([] if (cwd_config := get_working_dir_config()) is None else [cwd_config]),
        xdg_config,
        platform_config,
    ]
