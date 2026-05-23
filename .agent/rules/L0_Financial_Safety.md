---
trigger: always_on
---

---
type: rule
name: L0 – Hardcore Financial Safety Rules
---

# L0 – Hardcore Financial Safety Rules

**Priority: CRITICAL (Level 0 - Overrides everything)**

1.  **Capital Preservation Strictly First**: Preservation of capital overrides all other goals. Optimization or profit-seeking logic must never compromise principal safety.
2.  **Net Exposure Certainty**: No change may increase net exposure uncertainty. If a calculation or its side effect on exposure is unclear, the change must be rejected.
3.  **Invariant Protection**: Invariants protecting risk limits (e.g., max drawdown, max position size) must not be changed implicitly. Any change to these requires explicit confirmation of the new risk profile.
4.  **Shadow Mode Validation**: Any logical change involving entry/exit or position sizing MUST be verified in `shadow_mode` for at least one scanning cycle before being considered for live application (if applicable).
5.  **Decomposition of Complexity**: Large or unclear changes must be decomposed into small, verifiable chunks or rejected immediately.
6.  **Evidence > Confidence**: No unverifiable claims or "guesses" are allowed. Implementation must be backed by data or direct evidence from codebase inspection.
7.  **Do Nothing Safely**: When uncertain, "do nothing" is the preferred and always acceptable default action.
8.  **Workspace Inspection**: Workspace inspection (grepping, reading files) always overrides conversation memory to prevent "hallucinated" state.