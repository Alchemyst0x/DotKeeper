from __future__ import annotations

import os
from pathlib import Path

import yaml
from cyclopts import App
from rich.console import Console

from .cli import get_config_file_path, load_yaml_config, manage_symlinks, resolve
from .config import APP_AUTHOR, APP_NAME, APP_VERSION, DEFAULT_CONFIG, ensure_config_exists

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
def create_config_file(*, overwrite: bool = False) -> None:
    cwd = resolve(Path.cwd(), resolve_links=True)
    cfg_file = cwd / 'dotkeeper.yml'
    if not cfg_file.exists() or overwrite:
        cfg_file.write_text(yaml.safe_dump(DEFAULT_CONFIG.model_dump()))
        console.print(f'[green]Wrote config file to: {cfg_file}[/green]')
    elif cfg_file.exists():
        console.print(f'[yellow]Refusing to overwrite existing config file: {cfg_file} [/yellow]')
        console.print('[yellow]Use flag --overwrite to force.[/yellow]')


@app.command
def apply() -> int:
    _here: Path = Path(__file__).resolve().parent
    if _project_root := os.getenv('PROJECT_ROOT'):
        project_root: Path = resolve(_project_root)
    else:
        project_root: Path = _here.parents[1]

    os.environ['PROJECT_ROOT'] = str(project_root)
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
        console.print('[yellow]No config file found. Creating default config...[/yellow]')
        config_file = ensure_config_exists()
        console.print(f'[green]Created default config at {config_file}[/green]')
        config = DEFAULT_CONFIG
    except Exception as e:
        console.print(f'[red]Error loading config: {e}[/red]')
        return 1

    links_config = config.dotfiles.links
    console.print('[bold cyan]Managing symlinks...[/bold cyan]')

    manage_symlinks(console=console, config=links_config)

    return 0


def main() -> None:
    app()
