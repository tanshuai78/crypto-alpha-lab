# Ponytail — Project Minimality Adaptation

Apply the minimality ladder defined in [`.agent/skills/ponytail/SKILL.md`](../skills/ponytail/SKILL.md) (YAGNI → reuse existing codebase helpers → Python stdlib → native platform capability → shortest working diff) across design, planning, implementation, and review.

## Project Boundary Rules

1. **Precedence**: `L0 Financial Safety` and data-loss prevention → approved Design/Plan invariants and L2 research methodology → required SSOT/compatibility boundaries → Ponytail minimality.
2. **Never Simplify Away**: Trust-boundary validation, explicit failure handling, read-only input protection, point-in-time (PIT) causality, or approved verification obligations.
3. **Proportional Testing**: Follow [`.agent/rules/L1_Engineering_Process.md`](L1_Engineering_Process.md) (§2 Rule 4 & §3 Rule 15) for test and fixture requirements. Do not apply an unconditional "no fixtures" ban when local synthetic inputs or canonical upstream fixtures are the appropriate verification method; avoid unrequested test frameworks or redundant wrapper layers.
4. **Deliberate Ceilings**: Mark intentional simplifications that carry a known scaling or operational ceiling with a `# ponytail: <ceiling and upgrade condition>` comment.
