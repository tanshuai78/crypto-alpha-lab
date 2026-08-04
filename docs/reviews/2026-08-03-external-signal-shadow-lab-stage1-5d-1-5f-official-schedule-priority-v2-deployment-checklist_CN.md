# Stage 1.5D / 1.5F / 1.5G Official Schedule Priority V2 Deployment Checklist

**Root Suffix:** `7d_official_schedule_anchor_contract_v2_hotfix`

## Pre-Deployment Verification
1. Verify git clean state and record commit SHA locally.
2. Confirm local python tests pass: `make check`.
3. Confirm server free disk space >= 5G.

## Server Deployment Sequence
1. **Scoped Source Sync**:
   Sync `src/`, `scripts/`, `configs/base.py`, `docs/reviews/` to server. Exclude `data/`, `.git/`, `.venv/`, `__pycache__`.

2. **Per-file SHA256 Verification**:
   - `configs/base.py`
   - `src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py`
   - `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
   - `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
   - `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`

3. **Stage 1.5D Collector Launch**:
   Start Stage 1.5D with V2 output root `data/external_signal_shadow/stage1_5d_7d_official_schedule_anchor_contract_v2_hotfix`.
   Wait for `live_safety_gate_summary.json` to show `decision = stage1_5d_runtime_gate_ready`.
   Verify `formal_event_contract_versions_supported` contains `2` and `anchor_precedence_policy` is `official_schedule_priority_v1`.

4. **Stage 1.5F Observer Bootstrap**:
   Run `--bootstrap-watermark` for 1.5F with output root `data/external_signal_shadow/stage1_5f_7d_official_schedule_anchor_contract_v2_hotfix`.
   Verify `observer_root_contract.json` is written atomically with `root_mode = v2_production`.

5. **Stage 1.5F Observer Daemon Launch**:
   Start normal 1.5F process:
   `PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py --stage1-5d-events-glob "data/external_signal_shadow/stage1_5d_7d_official_schedule_anchor_contract_v2_hotfix/events/*.jsonl" --output-root data/external_signal_shadow/stage1_5f_7d_official_schedule_anchor_contract_v2_hotfix`

> Note: Ensure `events/*.jsonl` uses unescaped glob pattern and not escaped backslash pattern.
