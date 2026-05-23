---
trigger: always_on
description: Use this rule when refactoring code, implementing new business logic, adding or modifying logging, or performing general code maintenance and styling.
---

---
type: rule
name: L2 – Soft Preferences
---

# L2 – Soft Preferences

**Priority: NORMAL (Level 2 - Applied when higher levels are satisfied)**

1.  **Reversibility**: Prefer small, reversible changes over monolithic transformations.
2.  **Clarity over Cleverness**: Written code should be understandable by a human auditor. Avoid complex "clever" one-liners or highly abstract patterns unless necessary for performance.
3.  **Explicit > Implicit**: Prefer explicit configuration (in `config.py`) and explicit state management over implicit "magic" behaviors.
4.  **Logging Verbosity**: Ensure critical state transitions (e.g., entering/exiting positions, clearing cache) are logged at `INFO` or `SUCCESS` levels using `loguru`.
5.  **Graceful Degenerancy**: Ensure the system fails gracefully (e.g., catch API timeout, return `None` or empty cache) rather than crashing the main loop.