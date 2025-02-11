import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from rich.console import Console

from dotkeeper.cli import (
    backup_before_modifying,
    check_symlink_status,
    check_target_validity,
    get_config_file_path,
    interpolate,
    load_yaml_config,
    manage_symlinks,
    recurse_yaml_config,
)


def test_check_target_validity(fs: FakeFilesystem) -> None:
    target = Path('/home/user/dotfiles/.bashrc')
    assert check_target_validity(target) == 'MISSING'

    fs.create_file(target, contents='# content')
    assert check_target_validity(target) == 'EXISTS'


def test_backup_and_restore(fs: FakeFilesystem, console: Console) -> None:
    source = Path('/home/user/.bashrc')
    backup_dir = Path('/home/user/backup')

    fs.create_file(source, contents='original content')
    fs.create_dir(backup_dir)

    items_to_backup = [(source, source)]
    backup_before_modifying(
        console=console,
        backup_path=backup_dir,
        items_to_backup=items_to_backup,
    )

    assert (backup_dir / '.bashrc').read_text() == 'original content'


def test_interpolate() -> None:
    os.environ['TEST_VAR'] = 'test_value'

    assert interpolate('$TEST_VAR/path') == 'test_value/path'
    assert interpolate('${TEST_VAR}/path') == 'test_value/path'


def test_recurse_yaml_config() -> None:
    os.environ['DOTFILES'] = '/home/user/dotfiles'

    config = {
        '$HOME/.bashrc': '$DOTFILES/.bashrc',
        'nested': {
            '$HOME/.vimrc': '$DOTFILES/.vimrc',
        },
        'list': ['$HOME/.profile', '$DOTFILES/.profile'],
    }

    result = recurse_yaml_config(config)

    assert isinstance(result, dict)
    assert result['/home/user/.bashrc'] == '/home/user/dotfiles/.bashrc'
    assert result['nested']['/home/user/.vimrc'] == '/home/user/dotfiles/.vimrc'
    assert result['list'] == ['/home/user/.profile', '/home/user/dotfiles/.profile']


def test_load_yaml_config(fs: FakeFilesystem) -> None:
    config_path = Path('/home/user/config.yml')

    config_content = """
    $HOME/.bashrc: $HOME/dotfiles/.bashrc
    $HOME/.vimrc: $HOME/dotfiles/.vimrc
    """

    fs.create_file(config_path, contents=config_content)

    result = load_yaml_config(config_path)

    assert '/home/user/.bashrc' in result
    assert result['/home/user/.bashrc'] == '/home/user/dotfiles/.bashrc'


def test_get_config_file_path(fs: FakeFilesystem) -> None:
    os.environ['DOTKEEPER_CONFIG'] = '/home/user/env_config.yml'
    fs.create_file('/home/user/env_config.yml')
    assert get_config_file_path([]) == Path('/home/user/env_config.yml')

    del os.environ['DOTKEEPER_CONFIG']
    fs.create_file('/home/user/fallback.yml')
    assert get_config_file_path(['/home/user/nonexistent.yml', '/home/user/fallback.yml']) == Path(
        '/home/user/fallback.yml'
    )


def test_manage_symlinks(fs: FakeFilesystem, console: Console, monkeypatch: pytest.MonkeyPatch) -> None:
    dotfiles = Path('/home/user/dotfiles')
    if dotfiles.exists():
        fs.remove_object(str(dotfiles))

    fs.create_dir(dotfiles)
    fs.create_file(dotfiles / '.bashrc', contents='# bashrc content')
    fs.create_file(dotfiles / '.vimrc', contents='# vimrc content')

    config = {
        '/home/user/.bashrc': str(dotfiles / '.bashrc'),
        '/home/user/.vimrc': str(dotfiles / '.vimrc'),
    }

    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: True)

    manage_symlinks(console, config)
    assert Path('/home/user/.bashrc').is_symlink()
    assert Path('/home/user/.vimrc').is_symlink()
    assert Path('/home/user/.bashrc').resolve() == dotfiles / '.bashrc'

    fs.remove('/home/user/.bashrc')
    fs.create_symlink('/home/user/.bashrc', dotfiles / '.vimrc')
    manage_symlinks(console, config)
    assert Path('/home/user/.bashrc').resolve() == dotfiles / '.bashrc'

    fs.remove('/home/user/.vimrc')
    fs.create_file('/home/user/.vimrc', contents='local content')
    manage_symlinks(console, config)
    assert Path('/home/user/.vimrc').is_symlink()
    assert Path('/home/user/.vimrc').resolve() == dotfiles / '.vimrc'


def test_manage_symlinks_with_missing_targets(
    fs: FakeFilesystem,  # noqa: ARG001
    console: Console,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = {'/home/user/.bashrc': '/home/user/dotfiles/.bashrc'}

    answers = iter([False])
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: next(answers))

    manage_symlinks(console, config)
    assert not Path('/home/user/.bashrc').exists()


def test_manage_symlinks_restore(
    fs: FakeFilesystem, console: Console, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Path('/home/user/.bashrc')
    target = Path('/home/user/dotfiles/.bashrc')

    fs.create_file(source, contents='original content')
    fs.create_file(target, contents='new content')

    config = {str(source): str(target)}
    answers = iter([True, False])  # Yes to changes, No to confirmation
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: next(answers))

    manage_symlinks(console, config)
    assert not source.is_symlink()
    assert source.read_text() == 'original content'


def test_check_symlink_status(fs: FakeFilesystem) -> None:
    source = Path('/home/user/.bashrc')
    target = Path('/home/user/dotfiles/.bashrc')

    fs.create_file(target, contents='# bashrc content')
    assert check_symlink_status(source, target) == 'MISSING'

    fs.create_symlink(source, target)
    assert check_symlink_status(source, target) == 'CORRECT'

    wrong_target = Path('/home/user/dotfiles/.vimrc')
    fs.create_file(wrong_target, contents='# vimrc content')
    fs.remove(str(source))
    fs.create_symlink(source, wrong_target)
    assert check_symlink_status(source, target) == 'INCORRECT'

    fs.remove(str(source))
    fs.create_file(source, contents='different content')
    assert check_symlink_status(source, target) == 'NONLINK'
