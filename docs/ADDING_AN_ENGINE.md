# Adding a new enforcement engine (FR-ENGINE-2)

Integrating a new enforcement engine requires implementing **one adapter** and
adding **one config line**. Nothing else changes — not the constraint schema, the
importer/aggregation, the MCP server, or the validation harness (FR-ENGINE-2,
NFR-5). The bundled `conftest` adapter (`engine/adapters/conftest.py`) is a
worked second example alongside the reference `opa` adapter.

## 1. Implement the adapter

Create `src/cregistry/engine/adapters/<engine>.py` implementing the stable
`EngineAdapter` interface (`engine/interface.py`):

```python
from ..interface import EngineAdapter, EngineVerdict, Violation
from ...model import EnforcementBinding

class MyAdapter(EngineAdapter):
    name = "myengine"

    def __init__(self, options: dict | None = None) -> None:
        options = options or {}
        self.bin = options.get("bin", "myengine")

    def can_handle(self, binding: EnforcementBinding) -> bool:   # FR-ENGINE-3a
        return binding.engine == self.name

    def evaluate(self, artifact, policy: str) -> EngineVerdict:  # FR-ENGINE-3b
        # Run the REAL engine. Never raise for an unrunnable policy — return
        # EngineVerdict.errored(...) instead (NFR-2). Map findings to Violation
        # objects {message, rule?, resource?, path?, raw?, remediation?}.
        ...
        return EngineVerdict.failed_(self.name, policy, [Violation(message="...")])
```

Return only engine-level facts (`EngineVerdict` / `Violation`). Do **not** add
constraint-level concepts (severity, deprecation) — the orchestrator adds those.

## 2. Register it in config (FR-ENGINE-5)

Add one line under `engines:` in `registry.config.yaml`:

```yaml
engines:
  - name: myengine
    adapter: "cregistry.engine.adapters.myengine:MyAdapter"
    options: { bin: myengine }   # optional
```

The registry loads adapters by dotted path at runtime; no core code is edited.

## 3. Validate against the existing conformance suite (FR-ENGINE-2)

The engine-interface conformance suite (`engine/conformance.py`) is engine-
agnostic and data-driven. Validate your adapter by supplying `ConformanceCase`s
(policy, artifact, expected verdict) — no new harness code is required. The
harness already runs this suite against any configured adapter
(`harness/checks/engine.py`); the `conftest` adapter is wired through the very
same path and runs automatically once the `conftest` binary is installed.

That is the whole procedure. Constraints that reference the new engine
(`enforcement: [{ engine: myengine, policy: ... }]`) now validate through it, and
the anti-drift fixture cross-check (`integrity.py`) covers them automatically.
