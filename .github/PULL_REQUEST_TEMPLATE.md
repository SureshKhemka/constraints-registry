<!-- Thanks for contributing! Please fill this in so reviewers have context. -->

## What & why

<!-- What does this PR change, and why? Link the issue it addresses. -->

Closes #

## Type of change

- [ ] Bug fix
- [ ] New engine adapter
- [ ] New / updated constraint source
- [ ] Feature
- [ ] Docs
- [ ] Chore / refactor

## How was this verified?

<!-- Commands you ran and their result. -->

- [ ] `uv run pytest` passes
- [ ] `uv run cregistry-harness` is green
- [ ] Added/updated tests for the changed behavior

## Checklist

- [ ] Follows [CONTRIBUTING.md](../CONTRIBUTING.md) and the
      [Code of Conduct](../CODE_OF_CONDUCT.md)
- [ ] For a new engine: implements `EngineAdapter`, never raises from `evaluate`,
      is deterministic, reuses the SARIF seam (if SARIF), and is wired into the
      conformance suite — no changes to the schema/importer/MCP server/harness
- [ ] Docs updated (README / `docs/`) where user-facing behavior changed
- [ ] No secrets, credentials, or unrelated changes included
