"""Second engine adapter: Conftest (FR-ENGINE-2 demonstration).

This adapter exists to demonstrate FR-ENGINE-2: a new engine is integrated by
adding *only* a new adapter module plus a config line — no change to the
constraint schema, importer, MCP server, or harness. It is a real adapter that
shells out to the actual ``conftest`` binary; there is no stub. When ``conftest``
is not installed, the harness's engine checks SKIP (with a reason) rather than
fail — the OPA adapter remains the always-green reference (FR-ENGINE-4).

Conftest shares OPA's Rego policies and the conftest ``deny`` convention, so the
same policies and fixtures used by the OPA adapter validate this one too.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ...model import EnforcementBinding
from ..interface import EngineAdapter, EngineVerdict, Violation


class ConftestAdapter(EngineAdapter):
    name = "conftest"

    def __init__(self, options: dict | None = None) -> None:
        options = options or {}
        self.bin = options.get("bin", "conftest")
        self.timeout = options.get("timeout", 60)

    def can_handle(self, binding: EnforcementBinding) -> bool:
        return binding.engine == self.name

    @property
    def available(self) -> bool:
        return shutil.which(self.bin) is not None

    def evaluate(self, artifact: Any, policy: str) -> EngineVerdict:
        policy_path = Path(policy)
        if not policy_path.exists():
            return EngineVerdict.errored(self.name, policy, f"policy not found: {policy}")
        if not self.available:
            return EngineVerdict.errored(self.name, policy, f"conftest binary not found: {self.bin!r}")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(artifact, tf)
            input_path = tf.name
        try:
            proc = subprocess.run(
                [self.bin, "test", input_path, "--policy", policy, "--output", "json", "--all-namespaces"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            return EngineVerdict.errored(self.name, policy, f"conftest binary not found: {self.bin!r}")
        except subprocess.TimeoutExpired:
            return EngineVerdict.errored(self.name, policy, "conftest evaluation timed out")
        finally:
            Path(input_path).unlink(missing_ok=True)

        # conftest exits non-zero when there are failures; that is normal, not an
        # engine error. Distinguish by attempting to parse the JSON report.
        try:
            results = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return EngineVerdict.errored(
                self.name, policy, f"unparseable conftest output: {proc.stderr.strip() or proc.stdout.strip()}"
            )

        violations: list[Violation] = []
        for result in results:
            namespace = result.get("namespace")
            for failure in result.get("failures", []) or []:
                msg = failure.get("msg") if isinstance(failure, dict) else str(failure)
                violations.append(Violation(message=str(msg), rule=namespace, raw=failure))
        violations.sort(key=lambda v: (v.rule or "", v.message))

        if violations:
            return EngineVerdict.failed_(self.name, policy, violations)
        return EngineVerdict.passed_(self.name, policy)
