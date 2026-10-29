# `closure-revision` Skill Layout & Project Wiring

## Directory Structure

This project-owned skill resides in the repository at:

```text
.agent/skills/closure-revision/
├── SKILL.md
├── INSTALL.md
└── references/
    ├── design-plan-checklists.md
    ├── revision-control-packet.md
    └── revision-failure-patterns.md
```

## Project Maintenance Rules

1. **In-Repository Maintenance Only**:
   - Edit `closure-revision` files directly in place under `.agent/skills/closure-revision/` when authorized by an approved Plan.
   - **Never** unzip or copy an external bundle over `.agent/skills/` wholesale, as doing so can overwrite project-specific adaptations or sibling skills.
2. **Single Rule Authority (`L1`)**:
   - Routing for `closure-revision` is already defined in [`.agent/rules/L1_Engineering_Process.md`](../../rules/L1_Engineering_Process.md) (§2 Closure Revision Discipline) and summarized in [`AGENTS.md`](../../../AGENTS.md).
   - Do **not** copy-paste long duplicate routing blocks into `AGENTS.md`, `GEMINI.md`, or workflow files.

## Verification

```bash
test -f .agent/skills/closure-revision/SKILL.md
test -f .agent/skills/closure-revision/references/design-plan-checklists.md
test -f .agent/skills/closure-revision/references/revision-control-packet.md
test -f .agent/skills/closure-revision/references/revision-failure-patterns.md
```
