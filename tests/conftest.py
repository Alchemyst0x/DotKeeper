import os

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from rich.console import Console


@pytest.fixture
def console() -> Console:
    """Create a Rich console for testing."""
    return Console(force_terminal=True)


@pytest.fixture
def fs(fs: FakeFilesystem) -> FakeFilesystem:
    """Setup fake filesystem with home directory."""

    fs.create_dir('/home/user')
    fs.create_dir('/home/user/dotfiles')
    os.environ['HOME'] = '/home/user'
    return fs
