from typing import Any

from pydantic import BaseModel, Field


class DotfilesConfig(BaseModel):
    """Configuration for dotfiles management."""

    links: dict[str, str] = Field(
        default_factory=dict,
        description='Mapping of source paths to target paths for symlinks',
    )

    obfuscate: dict[str, list[str]] = Field(
        default_factory=lambda: {'file_names': []},
        description='Configuration for file obfuscation',
    )


class Config(BaseModel):
    """Root configuration model."""

    dotfiles: DotfilesConfig = Field(
        default_factory=DotfilesConfig,
        description='Dotfiles configuration settings',
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Config':
        """Create a Config instance from a dictionary.

        Parameters
        ----------
        data : dict[str, Any]
            Raw configuration dictionary

        Returns
        -------
        Config
            Validated configuration object
        """
        return cls.model_validate(data)
