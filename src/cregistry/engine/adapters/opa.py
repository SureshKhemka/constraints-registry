"""Reference engine adapter: Open Policy Agent (FR-ENGINE-4).

Invokes the real ``opa`` binary (``opa eval``) against a Rego policy — there is
no stub on the enforcement path. Follows the Conftest convention: a policy
signals failures via ``deny`` / ``violation`` rule sets; a non-empty set means
the artifact fails.

This module is the *only* code that knows anything OPA-specific. Per FR-ENGINE-2,
adding another engine is a sibling module like this one plus a config line.
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

_DENY_KEYS = {"deny", "violation", "violations"}


class OpaAdapter(EngineAdapter):
    name = "opa"

    def __init__(self, options: dict | None = None) -> None:
        options = options or {}
        self.bin = options.get("bin", "opa")
        self.query = options.get("query", "data")
        self.timeout = options.get("timeout", 60)

    # FR-ENGINE-3a
    def can_handle(self, binding: EnforcementBinding) -> bool:
        return binding.engine == self.name

    @property
    def available(self) -> bool:
        return shutil.which(self.bin) is not None

    # FR-ENGINE-3b
    def evaluate(self, artifact: Any, policy: str) -> EngineVerdict:
        policy_path = Path(policy)
        if not policy_path.exists():
            return EngineVerdict.errored(self.name, policy, f"policy not found: {policy}")
        if not self.available:
            return EngineVerdict.errored(self.name, policy, f"opa binary not found: {self.bin!r}")

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(artifact, tf)
            input_path = tf.name
        try:
            proc = subprocess.run(
                [self.bin, "eval", "--format", "json", "-i", input_path, "-d", policy, self.query],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError:
            return EngineVerdict.errored(self.name, policy, f"opa binary not found: {self.bin!r}")
        except subprocess.TimeoutExpired:
            return EngineVerdict.errored(self.name, policy, "opa evaluation timed out")
        finally:
            Path(input_path).unlink(missing_ok=True)

        if proc.returncode != 0:
            return EngineVerdict.errored(
                self.name, policy, f"opa exited {proc.returncode}: {proc.stderr.strip()}"
            )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return EngineVerdict.errored(self.name, policy, f"unparseable opa output: {exc}")

        violations = self._extract(data, policy)
        if violations:
            return EngineVerdict.failed_(self.name, policy, violations)
        return EngineVerdict.passed_(self.name, policy)

    def _extract(self, data: dict, policy: str) -> list[Violation]:
        try:
            value = data["result"][0]["expressions"][0]["value"]
        except (KeyError, IndexError, TypeError):
            return []
        out: list[Violation] = []
        for rule_path, entry in _walk(value, []):
            message, resource = _message(entry)
            out.append(Violation(message=message, rule=rule_path, resource=resource, raw=entry))
        # Stable ordering for determinism (NFR-1).
        out.sort(key=lambda v: (v.rule or "", v.message))
        return out


def _walk(node: Any, path: list[str]) -> list[tuple[str, Any]]:
    """Collect (dotted-rule-path, entry) for every deny/violation list in the tree."""
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, val in node.items():
            if key in _DENY_KEYS and isinstance(val, list):
                rule = ".".join(path + [key])
                found.extend((rule, entry) for entry in val)
            else:
                found.extend(_walk(val, path + [key]))
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            found.extend(_walk(item, path + [str(idx)]))
    return found


def _message(entry: Any) -> tuple[str, str | None]:
    if isinstance(entry, str):
        return entry, None
    if isinstance(entry, dict):
        msg = entry.get("msg") or entry.get("message") or json.dumps(entry, sort_keys=True)
        resource = entry.get("resource") or entry.get("resource_id")
        return str(msg), (str(resource) if resource is not None else None)
    return str(entry), None
