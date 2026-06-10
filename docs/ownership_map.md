# Module Ownership and Migration Map

This repository currently ships two import paths:

- Canonical runtime code under `src/tino_storm/**`.
- Legacy compatibility imports under `knowledge_storm/**`.

To reduce drift, implementation ownership is now explicitly defined.

## Canonical Ownership

| Domain | Canonical location | Notes |
| --- | --- | --- |
| Provider/search API (`search`, providers, ingestion, retrieval, skills, security, API/CLI) | `src/tino_storm/**` | All new features and fixes land here first. |
| Shared core primitives (`dataclass`, `interface`, `encoder`, `utils`, logging wrapper, RM/LM primitives) | `src/tino_storm/core/**` (plus owning modules in `src/tino_storm/**`) | Public top-level modules remain import-forwarders for compatibility. |
| STORM wiki + collaborative engines | `src/tino_storm/storm_wiki/**` and `src/tino_storm/collaborative_storm/**` | Legacy `knowledge_storm` mirrors are now shim-only. |
| Legacy namespace (`knowledge_storm`) | `knowledge_storm/**` | Compatibility facade only; no business logic ownership. |

## Migration Path

1. Prefer `tino_storm.*` imports in all new code.
2. Keep `knowledge_storm.*` files as thin import-forwarders during transition.
3. Remove a legacy shim only after downstream users have migrated and a deprecation window is complete.
4. Enforce anti-drift with `scripts/check_duplicate_modules.py` (run locally and in CI).

## Guardrail

`scripts/check_duplicate_modules.py` validates that when a module exists in both trees
(e.g. `knowledge_storm/storm_wiki/engine.py` and `src/tino_storm/storm_wiki/engine.py`),
the legacy copy is a thin forwarder into `tino_storm` rather than a second implementation.
