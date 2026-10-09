# Stage 1.5J-A Conformance Remediation Design Delta

**日期:** 2026-10-08  
**状态:** `draft_for_independent_review`  
**父级 Design:** `docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md`  
**父级 Design SHA-256:** `b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a`  
**目的:** 修复已证实的 J-A producer/strict-loader 与父级 Design 合同漂移，产生一个全新、可 closure-audit 的 replacement receipt。  
**本 Delta 不授权:** implementation、network、receipt generation、commit、push、deployment、SSH、replay、signal、paper trading、live trading 或下游 J-B 消费。

---

## 1. Confirmed Facts

1. 父级 J-A Design 已冻结：request intent/terminal exact schema、404=`http_not_found`、finite positive decimal CSV、以及 `[launch_time_ms, launch_time_ms + PRESENCE_WINDOW_MS]` 的全部相交 UTC dates。
2. 当前 J-A Core SHA `6caa599689fdba038a1d4d3d88cb7e774ac55637f1008567685c0736799316e1` 实际产生的 intent 缺少 `request_state,parent_article_id,symbol,utc_date`，并含未批准的 `created_at_utc`。
3. 当前 production root `stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z` 有两个 404 terminal，均为未批准 enum `http_non_200`；因此它不符合父级 journal contract。
4. 当前 Core 只请求 launch UTC date，未实现父级 Design 要求的全部相交日期；本旧 root 的 281 个 child 恰好均未跨午夜，所以该 drift 未被此 root 的现有数据触发。
5. 当前 CSV validator 使用 `float()`，未显式拒绝 non-finite `NaN` 或 infinity token。
6. 旧 root、原始 raw bytes 和其 manifest 必须保持 immutable；它不是可用于 J-B 的 admissible upstream，且不得靠修改 loader、manifest、journal 或补写 audit report 追认。

---

## 2. Scope And Non-Goals

### 2.1 In scope

- J-A request journal exact schema/enum 的 producer 与 strict-loader conformance。
- finite positive `Decimal` CSV validation。
- 由 `PRESENCE_WINDOW_MS` 生成完整 UTC-date set 与相应 logical package records。
- 新 completion audit、单次新 network authorization、新 `RUN_ID` replacement receipt，以及该 replacement receipt 的 Closure Audit。
- replacement receipt 的 authority packet 改为绑定本 Delta 及其后续 approved remediation Plan。

### 2.2 Explicit non-goals

- 不修改父级 J-A Design bytes、旧 J-A receipt、旧 authorization bytes、J-B measurement/reducer、1.5D/F/G/H/I、风险/执行代码或 VPS。
- 不修复、删除或重跑旧 root；不承诺 replacement run 与旧 root 的 catalog/parent/count projection 相同。
- 不改变 universe、catalog selector、frozen parser、archive provider、resource caps、network profile、authority flags、output state reducer或任何 Alpha/PIT/成本/执行语义。
- 不允许网络、receipt generation 或 J-B consumption，直至后续各自的显式授权。

---

## 3. Decisions And Root-Cause Repair

### 3.1 Journal contract

每个 admitted request 在 DNS/HTTP 前 append+fsync 一个 intent。Intent exact keys、无多余字段：

```text
event, request_id, request_kind, request_state, url,
parent_article_id, symbol, utc_date
```

其中 `event="request_intent"`、`request_state="admitted_pending"`；`parent_article_id/symbol/utc_date` 仅在该 request kind 不适用时为 `null`。`created_at_utc`、`completed_at_utc` 及任何未列字段均禁止。

每个 intent 恰有一个 append+fsync terminal。Terminal exact keys、无多余字段：

```text
event, request_id, request_state, http_status, transport_error,
response_relative_path, response_sha256, response_bytes
```

合法 terminal state 和字段组合严格继承父级 Design：

```text
response_persisted:       http_status=200; transport_error=null; response_* non-null; response_bytes>0
http_not_found:           http_status=404; transport_error=null; response_*=null
transport_inconclusive:  http_status=null; transport_error=nonempty string; response_*=null
response_rejected:        http_status is integer other than 200/404; transport_error=null; response_*=null
```

`http_non_200` 永远非法。Producer、summary reduction 和 strict loader 必须对同一 exact grammar 验证；loader 不能从宽接受 legacy intent/terminal。

### 3.2 Archive date and numeric contract

对每个 parser-declared `in_scope_usdt` child，唯一 required UTC date set 为所有与闭区间 `[launch_time_ms, launch_time_ms + PRESENCE_WINDOW_MS]` 相交的 UTC calendar dates，升序、无重复。每个 date 产生独立 logical identity `(parent_article_id,symbol,utc_date,"aggTrades","futures_um")`；同一 physical ZIP 可被多个 logical records 引用但只下载一次。缺任一 required date 的 archive response 必须保留为该 child 的 coverage gap，不能静默降为单 launch-date coverage。

CSV `price` 与 `quantity` 由原始 token 用 `Decimal` 解析，必须 `is_finite()` 且严格大于零。`NaN`、`sNaN`、`Infinity`、`-Infinity`、空字符串和非 decimal grammar 均为 package STOP；不得用 `float()` 作为 admissibility predicate。其他父级 ZIP/header/order/id/maker/resource contract 保持不变。

### 3.3 Replacement authority and identity

未来 remediation Core 必须把 `APPROVED_DESIGN_*` 改为本 Delta 的 path/SHA，把 `APPROVED_PLAN_*` 改为后续 remediation Plan 的 path/SHA；canonical authority bundle 随之为 `.git/plan-execution/stage1_5j_a/<REMEDIATION_PLAN_SHA256>/`。该变化只允许新 Core 产生/消费 replacement receipt。

新 network authorization 必须单次绑定：approved Delta SHA、approved remediation Plan SHA、new `AUTHORIZED_RUN_ID`、completion-audited Core/CLI/Config SHA、frozen parser SHA、network profile，并仍声明所有非网络 authority 为 `false`。旧 authorization 和旧 `RUN_ID` 不得复用。

---

## 4. Data, State And Compatibility Contract

### 4.1 Replacement receipt

新 receipt 的 `schema_version`、final tree、manifest、summary、review renderer、journal persistence、coverage reducer、four-state lifecycle、flock/fsync/rename/no-resume 继续遵守父级 Design 的 exact v1 contract。`authority_packet` key set 必须仍然精确为 `approved_design,approved_plan,audited_cli,audited_config,audited_core,frozen_parser,network_authorization`；不得增加 `parent_design` 或任何字段。`approved_design` 绑定本 Delta 的 canonical path/SHA，`approved_plan` 绑定 remediation Plan；本 Delta 顶部冻结的父级 Design path/SHA 是唯一的传递 provenance。任何 receipt 如果 authority packet 不符合 replacement identity、journal 不符合 §3.1、package-date set 不符合 §3.2 或 CSV 不符合 §3.2，strict loader 必须 `STOP`。

### 4.2 Legacy root handling

旧 root `stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z` 保持在原路径、只读且 immutable。replacement Core 的 public strict loader 必须拒绝它；拒绝是预期安全结果，不允许 fallback、兼容 alias 或人工重绑定。旧 root 状态仅可称为 `legacy_not_admissible_for_downstream`; 它不能作为 J-B、Alpha、PIT、成本或执行证据。

新 receipt 不必复制旧 root counts。每次 catalog/detail/archive response 都依照已冻结 universe 和父级 reducer记录；若 archive source 的当前历史可得性发生变化，它必须以 replacement receipt 的 evidence gap/reduction 明确呈现，不得通过与旧统计对齐来篡改事实。

### 4.3 Research boundary

本 Delta 仍是 deterministic data-provenance repair。独立单位、Alpha/economic mechanism、PIT decision evidence、成本、流动性、容量、MAE/MFE、promotion/kill、paper/live/execution 均为 `N/A`，理由是本阶段只修复 archive coverage contract，不产生价格结果或交易规则。

---

## 5. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-15J-A-R-01 | Replacement producer and loader accept only exact journal keys, exact state enums and exact field combinations in §3.1. |
| INV-15J-A-R-02 | Every admitted request has one durable intent before transport and exactly one durable terminal; 404 is `http_not_found`, never `http_non_200`. |
| INV-15J-A-R-03 | All UTC dates intersecting the frozen presence interval form package logical identities before archive reduction. |
| INV-15J-A-R-04 | CSV price/quantity are finite positive `Decimal`; invalid numeric token is a structural STOP. |
| INV-15J-A-R-05 | Replacement Core/CLI/Config, Delta and remediation Plan are independently completion-audited and exact-bound by new run authority. |
| INV-15J-A-R-06 | Old root is immutable and fail-closed under replacement loader; no mutation, compatibility alias or authority rebinding can make it downstream-admissible. |
| INV-15J-A-R-07 | Replacement receipt preserves all parent/child omissions as coverage evidence gaps and retains parent clustering. |
| INV-15J-A-R-08 | Parent flock, atomic staging/fsync/rename, collision/no-resume and exact sealed-tree loading remain unchanged. |
| INV-15J-A-R-09 | Replacement root must positive-load before isolated one-mutation Closure Audit probes; always-reject loader is insufficient. |
| INV-15J-A-R-10 | No implementation, network, receipt, J-B consumer, replay, signal, paper, live or execution authority is implied by this Delta. |

---

## 6. Producer / Loader / Consumer Matrix

| role | required behavior | prohibited behavior |
| --- | --- | --- |
| replacement producer | exact journal, date set, Decimal validation, atomic replacement publication | legacy output repair, compatibility journal, network without new authority |
| replacement strict loader | independent exact grammar/date/package/reducer/render replay | permissive legacy acceptance or source fallback |
| remediation CLI | delegate only to canonical `run_inventory(run_id)` | alternate writer, parameterized project root, transport bypass |
| receipt closure auditor | positive-load replacement root, then `/tmp` isolated mutations | mutate production root or bless old root |
| J-B / future consumer | no access until separate identity rebind and approval | use either old or replacement root now |

All governance flags and `RISK_LIVE_TRADING_ENABLED` remain `False`.

---

## 7. Verification And Fixture Provenance

Pre-network canonical GRVT catalog/detail/ZIP/CHECKSUM evidence is a component fixture only, not a complete J-A root. It may prove public parser, required-date helper, checksum/ZIP/CSV validator, reducer, renderer and private journal/lifecycle writer components; it must not be wrapped, renamed or supplemented into a purported complete root, and it must not be used for a public strict-loader positive load. Before the separately authorized replacement run, the public strict loader may receive only incomplete or malformed roots for fail-closed structural probes; those probes are not positive evidence. No handcrafted cross-boundary success dictionaries, authority packets or hashes are allowed. Pure date-set and Decimal-token unit tests may use local scalar inputs because they do not prove an upstream artifact boundary.

The remediation Plan must require at least:

1. Canonical component fixture -> parser, required-date helper, checksum/ZIP/CSV validator, reducer, renderer and private journal/lifecycle writer proof; no public strict-loader positive claim.
2. One-field journal mutations: missing `request_state`, extra `created_at_utc`, `http_non_200`, incoherent 404 fields -> loader STOP.
3. Controlled 404 transport -> exactly `http_not_found`; another non-200 -> exactly `response_rejected`.
4. Boundary timestamps crossing UTC midnight -> two required dates in ascending order; non-crossing -> one date.
5. `NaN`, `sNaN`, `Infinity`, `-Infinity`, zero and negative price/quantity -> package STOP; finite positive decimal -> pass.
6. Existing production root -> replacement public loader fail-closed without copying or altering it.
7. New run authority mismatch, network absent, wrong run ID or changed Core/CLI/Config -> transport cannot start.
8. Same `RUN_ID` dual process, crash staging, final-only and final-plus-staging lifecycle tests.
9. Actual pytest, Ruff, `anti_shortcut_scan.py` RC, `git diff --check`, no staged changes and `RISK_LIVE_TRADING_ENABLED is False`.

After the user separately authorizes a replacement network run, Receipt Closure Audit must positive-load that exact new root and perform one-at-a-time `/tmp` semantic mutations. It must include journal schema/enum, date-record membership, numeric token, summary/review/count, duplicate terminal, authority packet and manifest-artifact probes. It may not use the old root as a positive baseline.

---

## 8. Allowed Future Implementation Surface

A later approved remediation Plan may whitelist only:

```text
src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
configs/base.py  # only if a new exact SSOT constant is proven necessary
scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py  # only if wiring proof requires it
```

No J-B file is mutable in this remediation. Parent J-A Design, old receipt/raw files, frozen parser, 1.5D/F/G/H/I artifacts, execution/risk code, VPS and existing state documents are No-Touch.

---

## 9. Authority And Routing

1. This Delta requires independent Design review and explicit user Design approval before a remediation Plan may be written.
2. Approved remediation Plan plus user implementation authorization may permit code/test changes only; it cannot authorize network or receipt generation.
3. Completion Audit precedes a newly authorized one-time network run.
4. Replacement receipt then requires its own positive strict load and Receipt Closure Audit.
5. Only after that closure can J-B receive a narrow upstream identity + projection/cardinality rebinding Closure Confirmation. It must freeze the replacement J-A identity, its actual projection, and every dependent exact J-B cardinality; J-B anchor/horizon/Decimal/parent-aggregation measurement contract must not change. Any measurement-rule change requires a separate Design.

There are no implementation-path open questions. Current status is `evidence_insufficient`; safe action before approval is no-op.
