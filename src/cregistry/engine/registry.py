"""Config-driven engine-adapter registry (FR-ENGINE-2/5, NFR-2/5).

Adapters are declared in config as ``module:ClassName`` dotted paths and loaded
at runtime. Adding an engine is therefore a config edit plus a new adapter
module — no core code changes (FR-ENGINE-2). A single adapter that fails to load
is recorded and skipped; it does not crash the registry (NFR-2).
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from dataclasses import dataclass

from ..bundle import ImportedConstraint
from ..config import RegistryConfig
from ..model import EnforcementBinding
from .interface import EngineAdapter


@dataclass(frozen=True)
class AdapterLoadError:
    name: str
    adapter: str
    message: str

    def to_dict(self) -> dict:
        return {"name": self.name, "adapter": self.adapter, "message": self.message}


def _load_adapter(spec: str, options: dict) -> EngineAdapter:
    module_path, _, class_name = spec.partition(":")
    if not module_path or not class_name:
        raise ValueError(f"adapter spec must be 'module:ClassName', got {spec!r}")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    instance = cls(options=options) if options else cls()
    if not isinstance(instance, EngineAdapter):
        raise TypeError(f"{spec} does not implement EngineAdapter")
    return instance


class EngineRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, EngineAdapter] = {}
        self.load_errors: list[AdapterLoadError] = []

    @classmethod
    def from_config(cls, config: RegistryConfig) -> "EngineRegistry":
        reg = cls()
        for ec in config.engines:
            try:
                reg._adapters[ec.name] = _load_adapter(ec.adapter, ec.options)
            except Exception as exc:  # noqa: BLE001 - isolate adapter load failure (NFR-2)
                reg.load_errors.append(AdapterLoadError(ec.name, ec.adapter, repr(exc)))
        return reg

    def register(self, adapter: EngineAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def names(self) -> list[str]:
        return sorted(self._adapters)

    def get(self, name: str) -> EngineAdapter | None:
        return self._adapters.get(name)

    def for_binding(self, binding: EnforcementBinding) -> EngineAdapter | None:
        """First registered adapter that can handle the binding (FR-ENGINE-3a)."""
        for adapter in self._adapters.values():
            if adapter.can_handle(binding):
                return adapter
        return None


def required_engines(constraints: Iterable[ImportedConstraint]) -> set[str]:
    """Engines needed to validate a set of constraints. Advisory constraints have
    no bindings and contribute nothing — they require zero engines (FR-ENGINE-4)."""
    return {b.engine for ic in constraints for b in ic.constraint.enforcement}
