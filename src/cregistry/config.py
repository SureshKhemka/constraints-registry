"""Registry configuration (FR-SOURCE-1, FR-ENGINE-5, FR-NAMESPACE-2).

The configurable set of source repositories and engine adapters lives in a YAML
config file. Adding an engine adapter is a config change only (FR-ENGINE-2/5):
no core code is edited.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class SourceConfig(BaseModel):
    """A configured source repository (FR-SOURCE-1, FR-SOURCE-4).

    ``name`` is the namespace used to disambiguate ids (FR-NAMESPACE-1).
    ``precedence`` orders sources for conflict resolution (FR-NAMESPACE-2);
    higher wins.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    precedence: int = 0


class EngineConfig(BaseModel):
    """A configured engine adapter (FR-ENGINE-5).

    ``adapter`` is a dotted import path ``module:ClassName`` loaded at runtime by
    the engine registry, so new engines are added without touching core code.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    adapter: str
    options: dict = Field(default_factory=dict)


class RegistryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceConfig] = Field(default_factory=list)
    engines: list[EngineConfig] = Field(default_factory=list)
    # Precedence policy name (FR-NAMESPACE-2). Only "default" in V0.
    precedence_policy: str = "default"

    # Directory the config file lives in; relative source paths resolve against it.
    base_dir: Path = Field(default=Path("."), exclude=True)

    def source(self, name: str) -> SourceConfig | None:
        return next((s for s in self.sources if s.name == name), None)

    def resolved_source_path(self, source: SourceConfig) -> Path:
        p = Path(source.path)
        return p if p.is_absolute() else (self.base_dir / p)

    def resolved_policy_path(self, source_name: str, locator: str) -> Path | None:
        """Resolve an enforcement-binding policy locator to an absolute path.

        Locators are interpreted relative to the owning source's directory
        (FR-CONSTRAINT-3: the registry references the policy, it does not copy it).
        Returns None if the source is unknown.
        """
        src = self.source(source_name)
        if src is None:
            return None
        return self.resolved_source_path(src) / locator


def load_config(path: str | Path) -> RegistryConfig:
    path = Path(path)
    data = yaml.safe_load(path.read_text()) or {}
    cfg = RegistryConfig.model_validate(data)
    cfg.base_dir = path.resolve().parent
    return cfg
