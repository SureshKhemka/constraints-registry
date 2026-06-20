"""VH-VERSION — versioning (VH-VERSION-1, VH-VERSION-2).

VH-VERSION-1: a consumer can request a specific bundle version and receives that
version's constraints; omitting the version yields the latest (FR-VERSION-3).
VH-VERSION-2: deprecated constraints are still returned and flagged (FR-VERSION-4).
"""

from __future__ import annotations

from ...config import RegistryConfig, SourceConfig
from ...importer import import_sources
from ...store import BundleStore
from ..result import CheckResult

SECTION = "VH-VERSION"


def _pinned_vs_latest(config: RegistryConfig) -> CheckResult:
    base = config.base_dir / "scenarios" / "versions"
    cfg_v1 = RegistryConfig(sources=[SourceConfig(name="versions", path=str(base / "v1" / "src"))])
    cfg_v2 = RegistryConfig(sources=[SourceConfig(name="versions", path=str(base / "v2" / "src"))])

    b1 = import_sources(cfg_v1).bundle
    b2 = import_sources(cfg_v2).bundle

    store = BundleStore()
    store.add(b1)
    store.add(b2)  # latest

    distinct = b1.bundle_id != b2.bundle_id
    pinned = store.get(b1.bundle_id)
    latest = store.get()  # no version -> latest

    pinned_ids = {c.effective_id for c in pinned.constraints} if pinned else set()
    latest_ids = {c.effective_id for c in latest.constraints} if latest else set()

    pinned_ok = pinned is not None and pinned.bundle_id == b1.bundle_id and pinned_ids == {
        "versions/ver.a"
    }
    latest_ok = latest is not None and latest.bundle_id == b2.bundle_id and latest_ids == {
        "versions/ver.a",
        "versions/ver.b",
    }

    if distinct and pinned_ok and latest_ok:
        return CheckResult.ok(
            SECTION,
            "VH-VERSION-1",
            "pinned bundle returns its own constraints; default returns the latest",
            details=[{"pinned": b1.bundle_id, "latest": b2.bundle_id}],
        )
    return CheckResult.fail(
        SECTION,
        "VH-VERSION-1",
        "version selection failed",
        details=[
            {
                "distinct": distinct,
                "pinned_ok": pinned_ok,
                "latest_ok": latest_ok,
                "pinned_ids": sorted(pinned_ids),
                "latest_ids": sorted(latest_ids),
            }
        ],
    )


def _deprecation(config: RegistryConfig) -> CheckResult:
    bundle = import_sources(config).bundle
    dep = bundle.get("data-platform/legacy.s3-acl")
    if dep is None:
        return CheckResult.fail(
            SECTION, "VH-VERSION-2", "expected deprecated constraint not returned by bundle"
        )
    c = dep.constraint
    if c.deprecated and c.successor == "platform-security/aws.s3.no-public-access":
        return CheckResult.ok(
            SECTION,
            "VH-VERSION-2",
            f"deprecated constraint {dep.effective_id} still returned and flagged (successor: {c.successor})",
        )
    return CheckResult.fail(
        SECTION,
        "VH-VERSION-2",
        "deprecated constraint not correctly flagged",
        details=[{"deprecated": c.deprecated, "successor": c.successor}],
    )


def run(config: RegistryConfig) -> list[CheckResult]:
    return [_pinned_vs_latest(config), _deprecation(config)]
