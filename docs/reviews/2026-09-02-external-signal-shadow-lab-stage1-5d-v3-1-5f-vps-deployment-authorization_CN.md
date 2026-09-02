# Stage 1.5D V3 / Stage 1.5F VPS Deployment Authorization

**日期:** 2026-09-02  
**状态:** deployment_authorization_draft  
**Review Mode:** initial_contract  
**类型:** VPS deployment authorization and runbook governance; no code change

## 1. Authorization Target

本授权只覆盖已完成 completion audit 的 Stage 1.5D Historical Catalog Re-admission Hotfix，以及与其同源的新 Stage 1.5F root：

- Approved Design SHA-256: `6a5fbf17d3acbb8e3f7a977cdd46c1f9e2a3516813c3dc3934e590c59e29155b`
- Approved Plan SHA-256: `d36e65137f013acddd07ef21048a975d8f53fddd9bbbeaa51f8d273861e9fcf6`
- Completion-audit provenance: `/tmp/stage1_5d_v3_historical_catalog_re_admission_681fcfe038806f89f214aa1ad02ba00e53b7a68e/`
- Target checkout: `/root/crypto-alpha-lab`
- New-root suffix: `7d_historical_catalog_re_admission_hotfix_v3`

The exact `DEPLOY_COMMIT` is intentionally not prefilled. It must be a pushed, immutable 40-character commit SHA that contains the approved implementation and is recorded in the target preflight transcript.

## 2. Scope And Non-Goals

Allowed only after approval:

- Stop the named old Stage 1.5F session, then the named old Stage 1.5D session; preserve every old root unchanged.
- Checkout the exact reviewed `DEPLOY_COMMIT` only after no D/F writer remains in the shared checkout.
- Start exactly one fresh Stage 1.5D V3 root and, only after its gate is READY, one matching fresh Stage 1.5F root.
- Run the target-local preflight and acceptance commands in Review Section 7.12.

Not authorized:

- Reuse, migrate, repair, delete, backfill, or append to any old root.
- Treat bootstrap-preexisting announcements as live evidence; MARSCOIN and other articles present at bootstrap remain non-consumable.
- Change the BAPI/title/support parser or manually map the "牛来USDT" article to a symbol.
- Enable execution, alpha interpretation, paper trading, live trading, order endpoints, private APIs, or `RISK_LIVE_TRADING_ENABLED`.

## 3. Required Target Preconditions

Before any tmux stop or Git checkout, the VPS transcript must prove all of the following:

1. Target checkout is a non-shallow Git worktree; `data/external_signal_shadow` is ignored; worktree is clean.
2. `DEPLOY_COMMIT` exists in `origin`, resolves to the target checkout after detached checkout, and its local Design/Plan SHA-256 values equal Section 1.
3. The target `.venv` imports the Stage 1.5D and Stage 1.5F runners; `RISK_LIVE_TRADING_ENABLED is False`.
4. Root filesystem free space is at least 8 GiB; no storage blocker exists.
5. The current D/F sessions and roots are identified exactly. If the old F root has `active_observation_count > 0`, STOP rather than interrupt a live 12-hour observation.
6. There is exactly one old D writer and exactly one old F writer before the authorized cutover; after the manual stop, there are zero D/F writers.
7. The new D root and new F root do not exist, and their tmux session names do not exist.

## 4. Authorized Cutover And Acceptance

The only valid order is:

```text
record old-root summary
-> stop named old F session
-> stop named old D session
-> prove zero writers
-> checkout exact DEPLOY_COMMIT
-> start fresh D V3 root
-> wait for trusted bootstrap and READY D gate
-> verify scheduler metadata_version == 3 and non-null catalog_bootstrap_cutoff_ms
-> bootstrap fresh matching F root
-> start F
-> verify root binding, runtime attestation, storage, and admission state
```

The new D gate must be `READY`, `stage1_5d_runtime_gate_ready`, and `consumable_by_stage1_5f=true` before F bootstrap. The new F must have all three source-root IDs bound to the new D root, `consumer_runtime_attestation_verified=true`, `consumer_runtime_attestation_compromised=false`, `block_new_event_admission=false`, and storage state `ready`.

## 5. Failure And Rollback

- Any preflight failure: do not stop sessions or checkout code.
- After old sessions are stopped, any checkout, D bootstrap, D gate, F bootstrap, or F acceptance failure: stop only any newly created session, preserve all old and new roots, and do not restart old sessions against the changed shared checkout.
- Do not delete a lock, root, state file, JSONL, diagnostic, watermark, or raw payload to force a retry.
- Record the failure transcript and open a separate incident or deployment revision before another attempt.

## 6. Authority State

```text
implementation_complete = true
deployment_authorization_runbook_allowed = true
deployment_allowed = false

execution_feasibility_claim_allowed = false
alpha_interpretation_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
RISK_LIVE_TRADING_ENABLED = false
```

This document becomes deployment authority only after an external review freezes its exact SHA-256 and the user grants deployment approval for the named `DEPLOY_COMMIT`, VPS, old session names, and new root/session names.
