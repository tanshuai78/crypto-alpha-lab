# reviewing-implementation-plans

This project-owned skill reviews Implementation Plans before execution to ensure scope discipline, vertical task slicing, consequence-driven verification, and alignment with `.agent/rules/L1_Engineering_Process.md` and `.agent/rules/L2_Alpha_Research_Methodology.md`.

## Key Responsibilities

- **`Allowed Change Scope` enforcement**: verifies bounded implementation, verification, documentation, runtime artifact, and `Affected but unchanged` paths; blocks unscoped mutating commands (`ruff check --fix .`, `git clean -fdx`).
- **Vertical slicing & Ponytail minimality**: checks that tasks are independently verifiable slices with explicit dependencies, pruning speculative abstractions while preserving safety and approved contract invariants.
- **Targeted topology & consumer checks**: uses `rg` and source verification (plus targeted Graphify queries when shared boundaries change) to ensure downstream consumers are either updated in scope or proven compatible.
- **Consequence-driven verification**: aligns test requirements with `.agent/rules/L1_Engineering_Process.md` (`Rule 4` independent expected values, `Rule 15` fixture grading, and `Rule 17` consequence-driven persistent artifact checks without imposing ceremonial verifiers on local/exploratory tasks).
- **Safety & research honesty**: enforces `L0` execution isolation and (when applicable) `L2` point-in-time, sample-unit, and market-data evidence boundaries.

## Files

- [`SKILL.md`](SKILL.md): Core review instructions and output format.
- [`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md): Pre-flight checklist by impact category.
- [`PRESSURE_TESTS.md`](PRESSURE_TESTS.md): Adversarial review scenarios (`S1–S18` aligned).
