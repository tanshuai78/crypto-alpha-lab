# Stage 1.6D VPS Live Source Observation Deployment Authorization Design

- **日期:** 2026-08-25
- **状态:** `design_approved`
- **Review Mode:** `initial_contract`
- **类型:** deployment authorization and runbook governance; no code change
- **研究路线:** Stage 1.6 = Binance USD-M Futures Delisting；Stage 1.6D = VPS live source observation and PIT provenance
- **上游权威:** `2026-08-24-stage1-6-futures-delisting-route-map_CN.md`、`2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
- **代码基线:** `c98801bb99e7e0d9d472b9684db97a12f442bdb6`（起草时 HEAD；后续审批须绑定实际 `DEPLOY_COMMIT`）
- **不授权:** 源码、配置、测试、历史 sealed export、交易、paper trading、replay、alpha 或 execution change
- **门禁状态:** `implementation_plan_allowed=true`；`authorization_runbook_allowed=true`；`implementation_allowed=false`；`deployment_allowed=false`

---

## 1. Confirmed Facts

1. Stage 1.6A--C 已完成来源、历史 sealed export 和 G2 semantic source audit；其 `source_audit_passed=true` 仅证明历史来源/语义审计通过，不证明实时 point-in-time (PIT) 可用性、市场数据覆盖、replay 或 alpha。
2. 已有 live runner `scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py`，但 `stage1_6b_*` 是 legacy producer namespace：在人类路线中它承担 Stage 1.6D live observation，不能重命名历史模块或路径。
3. runner 只接受显式 `--live-public-readonly`；`RISK_LIVE_TRADING_ENABLED=False`。runner 的 live 模式是 `capture_mode=live_observed`，不会产生交易指令。
4. fresh live root 只能是 `data/external_signal_shadow/stage1_6b/live_observation/<run_id>` 的直接子目录；已存在 root 不能作为 fresh start。每 root 有 `.stage1_6b_writer.lock` 生命周期排他锁。
5. runner 在新 root 创建后、网络访问前，要求 target 的 v2 source-profile attestation；其路径、文件名、profile、contract attestation SHA 和 root 内复制件均受校验。
6. 启动门禁由现有 `Stage16BStorageGuard` 强制：目标文件系统 free space 至少 8 GiB；live root 上限 256 MiB；root 使用共享 `data/external_signal_shadow/.stage1_5_storage_guard.lock` 做写入 admission。
7. runner 是单线程、顺序轮询，间隔为 300 秒；epoch 最长 7 天。正常结束写 `terminal_status.json` 后 seal；source schema drift 写失败终态并退出，不 seal。
8. `--resume` 仅适用于已有、未 terminal、未 sealed 的同一 live root；它要求同一 `run_id`、`capture_mode`、v2 profile 和同一 attestation SHA，并在 client/network 构造前先完成 reconciliation checkpoint。
9. 旧 checklist `2026-08-19-...stage1-6b...deployment-checklist...` 是历史 read-only preflight 证据。其 UNITREE/1.5G 条目反映当时迁移背景，不能继续作为 Stage 1.6D 的永久业务依赖。

## 2. Assumptions

1. 目标 VPS 的 free space、活跃进程、锁、tmux session 和网络/来源 profile 当前状态未知；它们必须由目标机的当次 transcript 证明，不能从本地历史结果推断。
2. Stage 1.5D/F 在目标机上可能运行，也可能已结束。它们只构成共享主机资源/锁的条件门禁，不构成 Stage 1.6D 的数据依赖。
3. 目标 VPS 可以运行当前已审批的 `DEPLOY_COMMIT`。若 target 代码、依赖或配置与该 commit 不一致，部署停止而不是现场修补。

## 3. Root Cause / Core Issue

当前部署材料把三类不同事实混在一起：已完成的 Unitree/1.5G 历史工作、Stage 1.5 的共享主机安全、以及 Stage 1.6D 本身的 source/PIT observation 权限。结果是旧 checklist 既缺少明确启动/恢复/封签操作边界，又可能把已结束的业务观测误当作永久前置条件。

本 Design 不修改 live producer。它只冻结一次部署授权所需的事实、停止条件和后续 runbook 的唯一操作边界。

## 4. Decisions

1. **部署对象不变。** 1.6D 只部署既有 live runner；本 Design 及其后续 docs-only runbook 不允许修改 `src/`、`scripts/`、`configs/` 或测试。
2. **旧 checklist 保留为历史证据。** 不改写其日期、当时 UNITREE/1.5G 结论或原始命名。当前操作只使用后续新增的 1.6D runbook；路线地图和 document index 只做导航更新。
3. **每次 start 先做 target-local attestation。** 本地 historical attestation 不能搬运为 VPS 部署凭证。runbook 必须先在 target 的当前 selected Delisting catalog 中确定一个 non-empty article `code`，并立即将它作为 `--probe-article-id`；probe 自身仍必须从其同次 index response 验证该 ID 的成员关系。不得硬编码历史公告 ID。产出的 v2 attestation SHA 是该 start 的唯一 attestation authority。
4. **首启为 fresh root。** 首次部署不得带 `--resume`，不得复用任何历史或其他 1.6D root。`run_id`、tmux session 和 live root 必须在 preflight 时均不存在。
5. **恢复是同 root 的受控操作。** 因进程/主机中断而恢复时，只能使用 runner 的 `--resume` 分支；要求 root 未 terminal、未 sealed，并由同一 attestation SHA 和 reconciliation transcript 证明。任何失败 terminal 或已 sealed root 禁止 resume，必须保留证据并创建新的 incident/epoch decision。
6. **1.5 是条件性 co-tenancy check。** 若 1.5D/F 在 target 活跃，必须证明其官方 runtime summary/heartbeat/storage/lock 健康且 blocker 为空；若均未运行，必须证明没有对应 writer 或被持有的共享锁，且不触碰其 root。锁文件的存在本身不是 stale owner 证据，严禁删除它来“修复” preflight。1.5G 是本地离线复核，不是 VPS 资源门禁。UNITREE 是已结束历史背景，不是门禁。
7. **每个 epoch 是独立证据单元。** 正常 epoch 最长 7 天，须写 complete terminal status 并 seal export。下一 epoch 使用新 `run_id`、fresh root、fresh target preflight 和 fresh target attestation；不得向已 sealed root 写新 observation。
8. **日志与 root 隔离。** tmux pane 是默认运行日志载体；禁止将 stdout/stderr 重定向到 live root 或其任何子路径。若 runbook 提供持久化日志选项，路径必须在 live root family 之外，并明确标记为非证据、非 storage-guard accounting input。
9. **审批分层。** Design approval 只允许编写并审查 docs-only runbook。实际 VPS start 仍须在该 runbook 的 target transcript 全部 PASS 后，由用户对明确的 `DEPLOY_COMMIT`、target host、run ID 和 attestation SHA 单独授权。

## 5. Scope / Non-Goals

### In Scope

- 定义 Stage 1.6D target preflight、start、health、stop、seal、resume 和 rollback 的授权语义。
- 定义 Stage 1.5 shared-host checks 的 active/absent 分支。
- 定义后续 docs-only runbook 的唯一 authoritative location 和旧 checklist 的历史定位。

### Non-Goals

- 不修改 live runner、storage guard、source client、source schema、配置或测试。
- 不执行 VPS SSH、probe、tmux start、data deletion、sync、deployment 或 resume。
- 不重跑 1.6B historical backfill 或 1.6C audit。
- 不采集市场数据、不验证 PIT 结论、不做 replay、不评价 alpha。
- 不开启 `paper_trading_allowed`、`live_trading_allowed`、`execution_engine_allowed` 或任何交易权限。

## 6. Acceptance Invariants

- **INV-01 Commit and environment binding:** 每份 target preflight transcript 必须记录 `DEPLOY_COMMIT`；实际启动的 `git rev-parse HEAD` 必须与其相等，且工作树干净。target `.venv` 必须成功导入 live runner 和 `configs.base`，并通过 Section 13 所列的定向 Stage 1.6B probe/live runner regression suite。任何不相等、dirty 状态、解释器/import 或定向回归失败均 STOP。
- **INV-02 Fresh target attestation:** attestation 必须在 target 生成，schema 为 `stage1_6b_source_profile_probe_attestation_v2`，profile 为 `binance_public_web_bapi_en_delisting_catalog_v2`。`probe_article_id` 必须是 target 当次 selected catalog 的动态 `code`，并满足 probe 同次 selected catalog membership、headers/profile hash、路径及 `probe_attested_at_ms <= run_started_at_ms` 的既有校验。
- **INV-03 Root and writer exclusivity:** fresh start 的 run ID/root/session 均不存在，且没有同 root writer。resume 只允许既有 root 满足 Section 4 Decision 5 的所有条件。
- **INV-04 Shared-host safety:** target free space 必须不少于 8 GiB；root 必须位于 live_observation family；共享 storage lock 正常可用。若 1.5D/F 活跃，则其健康门禁必须 PASS；若未活跃，则不得存在其 active writer 或被持有的共享锁。lock-file path 存在不能单独构成 FAIL。
- **INV-05 Log-output hygiene:** stdout/stderr 不得重定向至 `data/external_signal_shadow/stage1_6b/live_observation/<run_id>` 或其子路径。tmux buffer 或该 root family 之外的非证据路径才可承载 operator log；日志不得被手工加入 root 或 sealed export。
- **INV-06 Read-only authority:** start 命令必须显式含 `--live-public-readonly`，不得包含交易、order、paper、replay、market-data 或 execution 参数；target 必须以 `.venv` 执行 `assert base.RISK_LIVE_TRADING_ENABLED is False`。
- **INV-07 Bounded runtime:** production epoch 使用现有 300 秒顺序轮询和不超过 7 天的 runtime bound；`--max-polls` 与短于 epoch 的 `--max-seconds` 只可用于非 production verification，不能冒充完整 1.6D epoch。
- **INV-08 Terminal and sealing:** normal completion 必须形成 `status=complete`、`terminal_reason=epoch_complete` 的 terminal status 后 seal；schema drift 或其他 failure terminal 不得 seal，且不得删除已写 evidence。
- **INV-09 No cross-epoch write:** sealed 或 terminal root 禁止恢复和继续写入；后续 epoch 必须 fresh root。原有 1.5 roots、1.6B historical roots、1.6C audit roots 均只读保留。
- **INV-10 No research overclaim:** 1.6D deployed/running/sealed 仅证明 live source observation evidence 的状态，不能把 `point_in_time_source_validated`、`market_data_coverage_passed`、`replay_allowed`、`trade_signal_allowed`、`paper_trading_allowed`、`live_trading_allowed`、`execution_engine_allowed` 或 `alpha_interpretation_allowed` 改为 true。
- **INV-11 Fail closed:** 任一 preflight、attestation、disk、lock、commit、co-tenancy 或 authorization check 失败，禁止 start、禁止替代参数、禁止删除 root；记录失败 transcript 后停止。

## 7. Producer / Writer / Loader / Consumer / Reviewer Impact Matrix

| Role | Existing authority | This Design's effect | Change allowed now |
|---|---|---|---|
| Source profile probe | target-local v2 attestation producer | 规定每次 start 的 target-local usage | No |
| Live runner | fresh/resume root lifecycle, lock, storage, terminal/seal | 规定 operator 可调用的条件 | No |
| Storage guard | host/root quota and shared lock | 作为 hard preflight authority | No |
| Historical producer and sealed exports | 1.6B historical evidence | 只读保留，不参与 live root | No |
| 1.6C adapter/audit consumer | historical source audit | 不成为 live deployment prerequisite beyond completed status | No |
| Stage 1.5D/F writers | optional shared host occupants | active/absent co-tenancy branch | No |
| Stage 1.5G reviewer | local offline reviewer | 明确不构成 VPS gate | No |
| Future 1.6D runbook | operator procedure | Design approval后可 docs-only 新建 | Documentation only |

## 8. Data / State / Temporal Contract

```text
Target preflight transcript
  -> DEPLOY_COMMIT + target host facts + co-tenancy branch
  -> target-local v2 probe attestation SHA/path
  -> explicit user deployment authorization
  -> fresh live root (or separately authorized same-root resume)
  -> sequential observation/checkpoint records
  -> terminal_status.json
  -> sealed_export only after normal completion
```

- **Fresh start state:** no target session, no existing live root, no root writer, fresh target attestation.
- **Running state:** one writer lock for one root; periodic source observations remain public-read-only.
- **Complete state:** `terminal_status.status=complete` and `terminal_reason=epoch_complete`, followed by a sealed export.
- **Failure state:** terminal failure such as `source_profile_schema_drift`; evidence remains, no sealed export, no same-root resume.
- **Interrupted state:** terminal and sealed artifacts both absent; only the existing `--resume` contract may reconcile it, using the same root and attestation SHA.
- **PIT meaning:** `first observed`/trusted detail availability is recorded as future live evidence. Historical publication time and a source audit PASS do not backfill first-observed time.

## 9. Failure Semantics / Recovery / Idempotency

| Condition | Required result | Operator action |
|---|---|---|
| Commit/config/dependency mismatch | STOP before probe/start | Restore target to approved commit; re-run all preflight checks |
| Target probe/profile/schema failure | STOP; no live root | Preserve probe output; do not substitute local attestation or alternate endpoint |
| Disk/lock/co-tenancy gate failure | STOP; no runner start | Resolve capacity or host ownership outside this route; re-run preflight |
| Duplicate fresh root/session | STOP | Choose a new run ID only after confirming the previous root state; never overwrite |
| Runner crash without terminal/seal | Eligible only for same-root resume contract | Record incident transcript; validate same attestation SHA and reconciliation before `--resume` |
| Complete or failure terminal | No resume | Preserve root; complete root is sealed only when runner did so; failure root remains failure evidence |
| Source profile schema drift | Failure terminal, no seal, no retry-by-alias | Stop collection and open a new source-contract design issue |
| Operator cancellation/interruption | Preserve root and evidence; it is not a complete terminal | Current runner has no approved graceful operator-stop handler. Do not fabricate a terminal file; treat it as an interrupted root and follow the same-root resume review, or retain it as incomplete evidence |

The runbook must never implement recovery by deleting a lock file, terminal status, checkpoint, attestation, raw payload or root directory.

## 10. Compatibility / Migration / Historical Artifacts

- No artifact migration exists in this change.
- Historical `stage1_6b/historical_backfill` sealed exports and 1.6C audit roots remain immutable evidence.
- Existing `stage1_6b_*` module/path names remain unchanged despite the human route label 1.6D.
- The old 2026-08-19 checklist remains a historical review artifact. The successor runbook must link to it for provenance but must not inherit its completed UNITREE/1.5G bullets as current gates.
- There is no rollback by changing source code or configs. Operational rollback is stop/no-start, preserve evidence, and leave all safety flags false.

## 11. Evidence and Fixture Provenance

| Evidence | Use | Limitation |
|---|---|---|
| Current runner/storage source and tests | Proves existing lifecycle/lock/storage behavior | Does not prove target VPS readiness |
| Stage 1.6B historical sealed exports | Proves historical source-capture contract | Does not prove live first-observed timestamps |
| G2 1.6C completed audit root | Proves historical source audit can pass | Does not authorize deployment, PIT, replay or alpha |
| Target-local preflight transcript | Required deployment evidence | Valid only for the named host, commit, run ID and attestation SHA |
| Target-local live root/sealed export | Future 1.6D observation evidence | Does not satisfy 1.6E market-data coverage or 1.6F mechanism/replay gates |

No synthetic fixture, cached local probe file or copied historical attestation can satisfy INV-02.

## 12. Safety / Authority Boundary

The following values remain false for this entire Design, its runbook, and any 1.6D execution:

```text
RISK_LIVE_TRADING_ENABLED
source_audit_passed              # live producer artifact authority remains false
point_in_time_source_validated
market_data_coverage_passed
replay_allowed
risk_veto_candidate
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
alpha_interpretation_allowed
```

A successful 1.6D epoch may add evidence for a future PIT assessment only. It cannot itself change any item above.

## 13. Verification Strategy for the Future Docs-Only Runbook

The post-approval runbook must provide copyable, fail-closed checks and expected PASS/STOP output for:

1. local-to-target commit identity, clean working tree, target `.venv` import check and the exact target regression command below;
2. target-local dynamic selection of a current selected Delisting catalog article `code`, then v2 probe membership verification and attestation SHA/path;
3. target free space, shared lock, root physical isolation and active/absent 1.5 co-tenancy branch;
4. fresh root/session/writer absence before start;
5. explicit `RISK_LIVE_TRADING_ENABLED is False` assertion, read-only command shape, log path outside live root and exact 7-day production bound;
6. running health: one writer, checkpoint/summary freshness, storage and blocker condition;
7. normal terminal/seal inspection and separate failure-terminal inspection;
8. interrupted-root resume preconditions, including proof that client/network construction follows reconciliation;
9. proof that all safety/authority flags remain false;
10. no-delete rollback/incident record.

The required target preflight commands are limited to the deployment-relevant suite, not the entire research test tree:

```bash
PYTHONPATH=src:. .venv/bin/python -c \
  "from configs import base; from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import run_live_source_observer; assert base.RISK_LIVE_TRADING_ENABLED is False; print('stage1_6d_target_environment=PASS')"

PYTHONPATH=src:. .venv/bin/pytest -q \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py \
  tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_source_profile_probe.py \
  tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py
```

The runbook is rejected if it makes target facts optional, accepts an attestation copied from another machine, bypasses a STOP condition, starts a second writer, or equates a sealed live root with an alpha/trading authorization.

## 14. Rollout / Rollback

### Rollout sequence

```text
Design review and user approval
  -> docs-only runbook governance plan/review
  -> fresh target preflight transcript
  -> user grants explicit deployment authorization for named facts
  -> one fresh 7-day read-only epoch
  -> terminal/seal review
```

No step implies the next step without its own recorded PASS/approval.

### Rollback

```text
preflight failure or missing authorization -> do not start
runtime failure/drift -> allow runner terminal behavior; preserve root
operator cancellation/interruption -> no manual terminal; preserve root as interrupted evidence
```

No rollback action may delete, alter or reuse evidence roots.

## 15. Open Questions

- **N/A for this Design.** Target-specific values (host free space, active 1.5 processes, target commit, target attestation SHA and chosen run ID) are execution facts, not Design choices. They are deliberately unresolved until a target-local preflight; any non-PASS value blocks deployment under INV-11.

## 16. Approval Transition

After independent Design review and explicit user approval, update only this document's metadata to:

```text
status = design_approved
implementation_plan_allowed = true
authorization_runbook_allowed = true
implementation_allowed = false
deployment_allowed = false
```

The next artifact is a docs-only implementation plan/runbook governance revision. Actual deployment remains blocked until the target transcript and explicit user deployment authorization exist.
