# Contributing to Constraint Registry

Thanks for your interest in contributing! This project is open to contributions
of all kinds — bug reports, new engine adapters, constraint sources, docs, and
ideas. This guide explains how to get set up, the conventions we follow, and how
to get a change merged.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## Ways to contribute

- **Report a bug** — open an issue using the **Bug report** template.
- **Request a feature** — open an issue using the **Feature request** template.
- **Add an enforcement engine** — implement one adapter (see below); this is the
  most common and most welcome kind of contribution.
- **Improve docs** — README, the `docs/` guides, or inline docstrings.
- **Security issue** — please do **not** open a public issue; see
  [SECURITY.md](SECURITY.md).

If your change is large or you're unsure about direction, open an issue to
discuss it first so we can align before you invest the effort.

---

## Development setup

You need **Python ≥ 3.11** and **[uv](https://docs.astral.sh/uv/)**.

```bash
git clone https://github.com/SureshKhemka/constraints-registry.git
cd constraints-registry

uv sync                       # create the venv + install all deps (incl. semgrep)
```

Optional external engines (only needed to run the parts that shell out to them;
tests and the harness **skip** gracefully when a binary is absent):

```bash
# macOS
brew install opa conftest checkov
# (semgrep is installed automatically by `uv sync`)
```

See the [Prerequisites](README.md#prerequisites) table in the README for the
full per-tool matrix.

---

## Running tests and the harness

```bash
uv run pytest                       # full unit/integration test suite
uv run pytest tests/adapters -q     # just the engine-adapter tests
uv run cregistry-harness            # end-to-end validation harness (exit 0/1)
```

The harness emits machine-readable JSON and exits non-zero on any failure — it is
what CI runs. A green local run before you push saves a round-trip.

> Tests that exercise a real engine binary are automatically skipped when that
> binary is not on `PATH`. CI installs the engines so those paths are covered
> there; you don't need every engine installed locally.

---

## Adding an enforcement engine (the common case)

Adding an engine is intentionally small: **one adapter module + one config line**,
with **no changes** to the constraint schema, importer, MCP server, or harness
(this is a hard architectural invariant — FR-ENGINE-2).

1. Read [`CONTRACTS.md`](CONTRACTS.md) — the frozen adapter seam — and
   [`docs/ADDING_AN_ENGINE.md`](docs/ADDING_AN_ENGINE.md).
2. Implement `EngineAdapter` (`name`, `can_handle`, `evaluate`) under
   `src/cregistry/engine/adapters/<engine>/`. If your engine emits **SARIF**,
   reuse the shared normalizer (`adapters/sarif/`) — do **not** re-parse SARIF.
3. **Never raise from `evaluate`.** A missing binary, unparseable output, timeout,
   or bad artifact must return `EngineVerdict.error`, not an exception (NFR-2).
   The orchestrator relies on this to fail open.
4. Make `evaluate` **deterministic** — two runs on the same `(artifact, policy)`
   must produce an identical `to_dict()` (sort violations; don't leak temp paths).
5. Register it in `registry.config.yaml` and add `ConformanceCase`s so the
   **existing** data-driven conformance suite validates it — no new harness code.
6. Add fixture cross-checks (a `pass` fixture that passes, a `fail` fixture that
   fails) under `tests/`.

The `opa`, `conftest`, `checkov`, and `semgrep` adapters are all worked examples.

---

## Coding conventions

- **Style**: match the surrounding code. Type hints on public functions,
  module/function docstrings that reference the relevant spec ID where one exists.
- **Boundaries**: engine adapters return only engine-level facts
  (`Violation`/`EngineVerdict`) — never constraint-level concepts (severity,
  deprecation). The orchestrator adds those.
- **Security**: no `shell=True`; pass subprocess args as a list; enforce timeouts;
  clean up temp files/dirs in `finally`; never execute the artifact under test.
- **Determinism**: imports and validations must be reproducible.
- Keep changes focused; unrelated refactors belong in their own PR.

---

## Commit and PR conventions

- **Branch** off `main`: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- **Commits**: use [Conventional Commits](https://www.conventionalcommits.org/)
  style subjects, e.g. `feat: add Trivy engine adapter`. Keep the subject in the
  imperative mood and under ~72 chars; explain the *why* in the body.
- **One logical change per PR.** Smaller PRs review faster.
- **Open a PR** against `main` using the PR template. Fill in what changed, why,
  and how you verified it. Link any related issue (`Closes #123`).
- **CI must be green** (`uv run pytest` + `uv run cregistry-harness`) and you
  should add/extend tests for the behavior you change.
- A maintainer will review; address feedback by pushing follow-up commits to the
  same branch. We squash-merge, so your branch history can stay messy.

---

## Reporting bugs well

A good bug report includes: what you did, what you expected, what happened, the
exact command, the relevant output/JSON, and your environment (OS, Python
version, engine versions). The harness/MCP JSON output is especially useful.

---

## License of contributions

This project is licensed under [Apache-2.0](LICENSE). Unless you state otherwise,
any contribution you intentionally submit for inclusion is licensed under the
same terms, per section 5 of the Apache License. You retain copyright to your
contributions.

Thanks again — we're glad you're here. 🙌
