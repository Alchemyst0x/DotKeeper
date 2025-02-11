import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory
from typing import Any, Literal, cast

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from .config import ensure_config_exists
from .models import Config

load_dotenv()


@dataclass
class LinkStatus:
    source: Path | str
    target: Path | str
    status: Literal['CORRECT', 'MISSING', 'INCORRECT', 'NONLINK']
    style: Literal['green1', 'yellow1', 'red1']


def expand_path(path: Path | str) -> Path:
    return Path(os.path.expanduser(path)).expanduser()


def resolve(path: Path | str, *, resolve_links: bool = False) -> Path:
    """Resolve and expand a path, optionally following symlinks.

    Parameters
    ----------
    path : Path | str
        Path to resolve
    resolve_links : bool, default=False
        Whether to resolve symlinks

    Returns
    -------
    Path
        Resolved path
    """

    return expand_path(path) if not resolve_links else expand_path(path).resolve()


def interpolate(value: str) -> str:
    """Interpolate environment variables in a string.

    Parameters
    ----------
    value : str
        String containing environment variables to interpolate

    Returns
    -------
    str
        String with environment variables replaced
    """
    value = Template(value).substitute(os.environ)
    return os.path.expandvars(value)


def recurse_yaml_config(
    config: dict[str, Any] | list | str,
) -> dict[str, Any] | list | str:
    """Recursively interpolate environment variables in a YAML config.

    Parameters
    ----------
    config : dict[str, Any] | list | str
        Configuration to process

    Returns
    -------
    dict[str, Any] | list | str
        Processed configuration with interpolated values
    """
    if isinstance(config, dict):
        return {interpolate(k): recurse_yaml_config(v) for k, v in config.items()}
    if isinstance(config, list):
        return [recurse_yaml_config(item) for item in config]
    if isinstance(config, str):
        return interpolate(config)
    return config


def check_symlink_status(
    source: Path | str, target: Path | str
) -> Literal['MISSING', 'NONLINK', 'CORRECT', 'INCORRECT']:
    """Check the status of a symlink.

    Parameters
    ----------
    source : Path | str
        Path to the symlink
    target : Path | str
        Path the symlink should point to

    Returns
    -------
    Literal['MISSING', 'NONLINK', 'CORRECT', 'INCORRECT']
        Status of the symlink:
        - MISSING: source doesn't exist
        - NONLINK: source exists but isn't a symlink
        - CORRECT: symlink points to correct target
        - INCORRECT: symlink points to wrong target
    """
    source, target = resolve(source), resolve(target)
    if not source.exists():
        return 'MISSING'
    if not source.is_symlink():
        return 'NONLINK'
    if source.resolve() == target.resolve():
        return 'CORRECT'
    return 'INCORRECT'


def check_target_validity(target: Path | str) -> Literal['EXISTS', 'MISSING']:
    """Check if the target path exists.

    Parameters
    ----------
    target : Path | str
        Path to check for existence

    Returns
    -------
    Literal['EXISTS', 'MISSING']
        Status of the target path
    """
    target_path = resolve(target)
    return 'EXISTS' if target_path.exists() else 'MISSING'


def backup_before_modifying(
    *,
    console: Console,
    backup_path: Path,
    items_to_backup: list[tuple[Path, Path]],
) -> None:
    """Backup files and directories before modification.

    Parameters
    ----------
    console : Console
        Rich console for output
    backup_path : Path
        Directory to store backups
    items_to_backup : list[tuple[Path, Path]]
        List of (original, source) paths to backup
    """
    for original, source in items_to_backup:
        if source.exists():
            backup_target = backup_path / source.name
            if source.is_dir():
                shutil.copytree(source, backup_target)
            else:
                shutil.copy2(source, backup_target)
            console.print(f'[blue]Backed up {original} to {backup_target}[/blue]')


def preview_changes(
    *,
    console: Console,
    correct: list[str],
    missing: list[str],
    incorrect: list[str],
    nonlink: list[str],
) -> None:
    """Display a table of symlink statuses.

    Parameters
    ----------
    console : Console
        Rich console for output
    correct : list[str]
        List of correct symlinks
    missing : list[str]
        List of missing symlinks
    incorrect : list[str]
        List of incorrect symlinks
    nonlink : list[str]
        List of non-symlink items
    """

    table = Table(title='Symlink Status')
    table.add_column('Source', justify='left', style='cyan', no_wrap=True)
    table.add_column('Target', justify='left', style='cyan', no_wrap=True)
    table.add_column('Link Status', justify='left', style='cyan', no_wrap=True)
    table.add_column('Target Status', justify='left', style='cyan', no_wrap=True)

    all_statuses = [
        *[LinkStatus(source, target, 'CORRECT', 'green1') for source, target in correct],
        *[LinkStatus(source, target, 'MISSING', 'yellow1') for source, target in missing],
        *[LinkStatus(source, target, 'INCORRECT', 'red1') for source, target in incorrect],
        *[LinkStatus(source, target, 'NONLINK', 'red1') for source, target in nonlink],
    ]

    for status in all_statuses:
        target_status = check_target_validity(status.target)
        table.add_row(
            str(status.source),
            str(status.target),
            f'[{status.style}]{status.status}[/{status.style}]',
            '[green1]EXISTS[/green1]' if target_status == 'EXISTS' else '[red1]MISSING[/red1]',
        )

    console.print(table)


def load_yaml_config(
    config_path: Path | str,
) -> Config:
    """Load and process a YAML configuration file.

    Parameters
    ----------
    config_path : Path | str
        Path to YAML config file

    Returns
    -------
    Config
        Processed configuration with interpolated values
    """
    with Path(config_path).open() as f:
        raw_config = yaml.safe_load(f)

    processed_config = cast(dict, recurse_yaml_config(raw_config))
    return Config.from_dict(processed_config)


def get_config_file_path(
    possible_file_names: Sequence[Path | str],
    env_variable: str = 'DOTKEEPER_CONFIG',
) -> Path:
    """Find the configuration file path.

    Parameters
    ----------
    possible_file_names : Sequence[Path | str]
        List of possible config file paths to check
    env_variable : str, default='DOTKEEPER_CONFIG'
        Environment variable name for config path

    Returns
    -------
    Path
        Path to the found configuration file

    Raises
    ------
    FileNotFoundError
        If no configuration file is found
    """

    if _yaml_confg := os.getenv(env_variable):
        return resolve(_yaml_confg)

    for cfg in possible_file_names:
        if (_yaml_confg := Path(cfg)).exists():
            return resolve(_yaml_confg)
    return ensure_config_exists()


def manage_symlinks(console: Console, config: dict) -> None:
    """Manage symlinks according to configuration.

    Creates, updates, and repairs symlinks based on the provided configuration.
    Includes backup and restore functionality for safety.

    Parameters
    ----------
    console : Console
        Rich console for output
    config : dict
        Configuration mapping source paths to target paths
    """

    correct_links = []
    incorrect_links = []
    missing_links = []
    nonlink_items = []

    for source, target in config.items():
        source_path = Path(source).expanduser()
        target_path = Path(target).expanduser()

        status = check_symlink_status(source_path, target_path)

        if status == 'CORRECT':
            correct_links.append((source_path, target_path))
        elif status == 'MISSING':
            missing_links.append((source_path, target_path))
        elif status == 'INCORRECT':
            incorrect_links.append((source_path, target_path))
        elif status == 'NONLINK':
            nonlink_items.append((source_path, target_path))

    preview_changes(
        console=console,
        correct=correct_links,
        missing=missing_links,
        incorrect=incorrect_links,
        nonlink=nonlink_items,
    )

    if not (incorrect_links or missing_links or nonlink_items):
        console.print('[green]Everything looks good. No changes needed.[/green]')
        return

    missing_targets = []
    for _, target in incorrect_links + missing_links + nonlink_items:
        if check_target_validity(target) == 'MISSING':
            missing_targets.append(target)

    if missing_targets:
        console.print('[red]Warning: The following targets do not exist:[/red]')
        for target in missing_targets:
            console.print(f'[red]  - {target}[/red]')
        if not Confirm.ask('Continue anyway?'):
            console.print('[yellow]Exiting without making any changes[/yellow]')
            return

    if not Confirm.ask('Do you want to apply all changes?'):
        console.print('[yellow]Exiting without making any changes[/yellow]')
        return

    with TemporaryDirectory() as backup_dir:
        backup_path = Path(backup_dir)
        items_to_backup = [(source, source) for source, _ in incorrect_links + nonlink_items]
        backup_before_modifying(console=console, backup_path=backup_path, items_to_backup=items_to_backup)

        for source, target in incorrect_links + missing_links + nonlink_items:
            source = Path(source)
            if source.exists() or source.is_symlink():
                if source.is_dir() and not source.is_symlink():
                    shutil.rmtree(source)
                    console.print(f'[red]Removed directory {source}[/red]')
                else:
                    source.unlink()
                    console.print(f'[red]Removed {source}[/red]')

            source.symlink_to(target)
            console.print(f'[green]Created symlink: {source} -> {target}[/green]')

        if not Confirm.ask('Is everything correct?'):
            console.print('[yellow]Restoring from backup...[/yellow]')
            for backup in backup_path.iterdir():
                if (
                    original := next((orig for orig, src in items_to_backup if src.name == backup.name), None)
                ) and original.exists():
                    if original.is_dir():
                        shutil.rmtree(original)
                    else:
                        original.unlink()

                if backup.is_dir() and original:
                    shutil.copytree(backup, original)
                elif original:
                    shutil.copy2(backup, original)

                console.print(f'[yellow]Restored {original} from backup[/yellow]')
            console.print('[green]Restore completed[/green]')
