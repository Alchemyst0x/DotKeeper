from __future__ import annotations

import os
from pathlib import Path

from cyclopts import App
from rich.console import Console

from .cli import get_config_file_path, load_yaml_config, manage_symlinks, resolve
from .config import APP_AUTHOR, APP_NAME, APP_VERSION, DEFAULT_CONFIG

app = App(
    name='dk',
    version=APP_VERSION,
    console=(
        console := Console(
            no_color=os.getenv('NO_COLOR') is not None,
            force_terminal=True,
        )
    ),
)


@app.command
def apply() -> int:
    _here: Path = Path(__file__).resolve().parent
    if _project_root := os.getenv('PROJECT_ROOT'):
        project_root: Path = resolve(_project_root)
    else:
        project_root: Path = _here.parents[1]

    os.environ['PROJECT_ROOT'] = str(project_root)
    _default_config_name: str = 'dotkeeper.yml'
    _maybe_config_names: tuple[str, ...] = (
        'config.yml',
        'config.yaml',
        'dotkeeper.yml',
        'dotkeeper.yaml',
        'dotkeeper_config.yml',
        'dotkeeper_config.yaml',
    )

    try:
        maybe_configs: list[Path | str] = [Path(project_root, fn) for fn in _maybe_config_names]
        config = load_yaml_config(get_config_file_path(maybe_configs))
    except FileNotFoundError:
        console.print('[red]Unable to locate DotKeeper config file.[/red]')
        return 1

    links_config = config['dotfiles']['links']
    console.print('[bold cyan]Managing symlinks...[/bold cyan]')

    manage_symlinks(console=console, config=links_config)

    return 0


@app.command(name='version')
def print_version() -> None:
    console.print(APP_VERSION)


@app.command(name='app-name')
def print_app_name() -> None:
    console.print(APP_NAME)


@app.command(name='app-author')
def print_app_author() -> None:
    console.print(APP_AUTHOR)


def main() -> None:
    app()
