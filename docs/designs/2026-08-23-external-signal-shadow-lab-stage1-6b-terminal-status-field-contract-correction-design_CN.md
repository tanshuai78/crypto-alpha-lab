# Stage 1.6B TerminalStatus Serialized Field Contract Correction

- **日期:** 2026-08-23
- **状态:** `design_under_closure_revision`
- **类型:** narrow parent-contract documentation correction
- **适用范围:** 已批准的 Stage 1.6B canonical official-source capture / sealed-export contract
- **不授权:** 代码、schema migration、collector、storage、sealed export rewrite、deployment 或 trading change

---

## 1. Confirmed Facts

`TerminalStatusRecord` 的已实现、已验证、已封签的 serialized field 是 `terminal_reason`：

```text
schema_version, capture_mode, run_id, source_profile_id,
status, terminal_reason, final_checkpoint_id, terminated_at_ms
```

当前 Stage 1.6B loader、tests 与 reference sealed export 都使用该 field。父 Design 的 Section 7.3 / Section 8 有两处写作 `terminal_status.reason`；这是 documentation field-name drift，不是第二个 schema version 或 compatibility target。

## 2. Decision And Exact Correction

本 correction 的优先级高于父 Design 中与此冲突的两处表述。对于 `stage1_6b_terminal_status_v1`：

```text
terminal_status.terminal_reason == historical_backfill_complete
```

是 historical completed-export acceptance 的唯一 terminal-reason predicate。

不得读取 `terminal_status.reason`，不得使用 `reason` / `terminal_reason` compatibility alias，亦不得修改既有 sealed export 或 Stage 1.6B producer。

父 Design 所有 `terminal_status.reason = ...` 的叙述性生命周期示例亦应理解为 `terminal_status.terminal_reason = ...`；值域和 lifecycle ordering 保持不变。

## 3. Scope / Non-Goals

本 correction 只统一 serialized field name。它不改变 `historical_completion_precondition`、HistoricalCoverage predicate、checkpoint ordering、manifest hashing、consumer acceptance、storage budget 或 restart semantics。

## 4. Contract Impact Matrix

| Role | Required behavior |
|---|---|
| Stage 1.6B producer | Continue serializing the existing `terminal_reason` field. |
| Stage 1.6B sealed-export loader | Continue requiring `terminal_reason == historical_backfill_complete`. |
| Stage 1.6A offline consumer | Read only `terminal_reason`; reject a missing or mismatched field. |
| Reviewer/operator | Treat `reason` as a stale document spelling, never as a valid artifact field. |

## 5. Failure Semantics, Persistence, Compatibility

Missing, non-string or mismatched `terminal_reason` is a fail-closed completed-export rejection. Existing `stage1_6b_terminal_status_v1` artifacts remain valid without migration because their serialized field already matches this correction. No new persistence, restart or crash behavior is introduced.

## 6. Verification

Before any downstream implementation plan is approved, preflight must verify the exact key set above on the caller-supplied reference export and confirm that `load_sealed_export()` accepts the same artifact only when `terminal_reason` equals `historical_backfill_complete`.

## 7. Safety / Rollback / Open Questions

Safety flags and all collection/trading permissions are unchanged. Rollback is documentation-only: do not use the superseded `reason` spelling for any implementation. Open Questions: `N/A`; this correction does not introduce a runtime decision.
