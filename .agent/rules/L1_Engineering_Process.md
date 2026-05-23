---
trigger: always_on
---

---
type: rule
name: L1 – Superpowers Engineering Process Rules
---

# L1 – Superpowers Engineering Process Rules

**Priority: HIGH (Level 1 - Guides how work is done)**

1.  **Workflow Discipline**: Non-trivial tasks must follow structured workflows (e.g., plan → implement → verify).
2.  **Mandatory Brainstorming**: Call `brainstorming` Skill before implementation when intent, technical design, or financial risk is unclear.
3.  **Mandatory Planning**: Call `writing-plans` Skill and get confirmation BEFORE modifying any code in `src/`.
4.  **TDD for Logic**: Use `test-driven-development` Skill for any changes to core logic (analyzer, position sizer, safety checks). Write tests before code.
5.  **Systematic Debugging**: Use `systematic-debugging` Skill for any bug report or unexpected behavior. Do not "guess" a fix.
6.  **Protocolized Code Review**: Before finalizing significant changes, use `requesting-code-review` Skill. You MUST define the scope using Git SHAs (`BASE_SHA` to `HEAD_SHA`) to ensure technical precision.
7.  **Defensive Reception**: When receiving feedback, follow `receiving-code-review` Skill. 
    - **Prohibited**: Performative agreement (e.g., "You're right", "Great point", "Thanks").
    - **Required**: Restate technical requirements, perform objective verification (grep/tests), and provide reasoned pushback if a suggestion violates YAGNI or project invariants.
8.  **Verification > Assertion**: Completion of a task requires hard verification (automated tests passing or log evidence), not mere assertion. Any logic change from a review MUST be re-verified via TDD.
9.  **Syncing State**: Always check `main.py` and `config.py` at the start of a session to sync with the current deployment state.