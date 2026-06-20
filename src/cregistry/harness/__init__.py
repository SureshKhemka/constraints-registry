"""Validation harness (Section 7).

A separate, runnable component that proves the registry and its constraint set
are internally consistent. It tests the registry; it is distinct from
FR-VALIDATE (which validates user artifacts). It emits machine-readable JSON and
exits non-zero on any failure (VH-OUTPUT-1).
"""
