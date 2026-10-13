# Stage 1.5J-B Historical `aggTrades` Launch-Anchor Price-Response Exploratory Design

**日期:** 2026-10-07  
**状态:** `revised_draft_for_closure_confirmation`  
**研究模式:** `exploratory_descriptive_only`  
**范围:** 只读消费一个 closure-audited Stage 1.5J-A root，对其中已验证的 USD-M USDT perpetual `aggTrades` 做固定 launch-anchor 的历史成交打印描述归约。  
**本 Design 不授权:** implementation、network、receipt generation、strategy/simulator replay、signal、PnL、execution、paper trading、live trading、commit、push、deployment 或 SSH。

`replay_allowed=false` 专指策略、模拟盘或执行 replay。本阶段允许的仅是下文冻结的、离线且确定性的 historical descriptive reduction；它不建立 PIT 决策证据、可执行价格、Alpha、经济优势或执行可行性。

---

## 0. 修订边界与上游证据状态

本次只修复 closure-audit 的 P0-01 至 P0-07、P1-01 至 P1-04 及其直接 sibling proof edges。J-A 是 immutable 输入；J-B 的所有权限仍为 `false`。本 Design 不把任何 future authority 写入磁盘，也不自行批准后续 Plan 或 receipt。

J-A 输入身份已冻结于本 Design，但其对外独立验证需要 `§10.1` 的最小证据包。该包未提供给 reviewer 前，以下 J-A numeric projection 仅是 **frozen upstream claim**，不是本轮 reviewer 已独立确认的事实；缺包时必须保持 `EVIDENCE_GAP`，不得进入 Plan。

---

## 1. Frozen Upstream Authority

### 1.1 唯一 J-A 输入

```text
J_A_RUN_ID = stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z
J_A_OUTPUT_PARENT = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory
J_A_ROOT_RELATIVE_PATH = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/
  stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z

J_A_MANIFEST_SHA256 = f0f45e352441d3ca3b60bbe48c4e23d08ad9c41bfb7f8623644f6074530af81b
J_A_SUMMARY_SHA256  = b8b00bb8f2e8684f64434eaad55b941f5096cfa2f9465489204e0f1208ce04ab
J_A_REVIEW_SHA256   = af1a4ea0056d838afed3439a58530c9530c226f2f8caac099db3afb406534519
J_A_JOURNAL_SHA256  = 325dfc6f8ca0ca7402c910084d13622a5f665d0604a9888b6eaba1f2832d1a20

J_A_DESIGN_SHA256 = b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a
J_A_PLAN_SHA256   = fa7d2ac23a605163a3ceb476efe4c5823b94e16ef9944ced173a2cff9d07279f
J_A_CORE_PATH = src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
J_A_CORE_SHA256 = 6caa599689fdba038a1d4d3d88cb7e774ac55637f1008567685c0736799316e1
J_A_LOADER_SYMBOL = load_verified_stage1_5j_a_historical_archive_coverage_root
```

J-B producer 和 J-B strict loader 均按以下顺序准入。任一步失败为 `STOP=stage1_5j_b_upstream_authority_mismatch`，不得读取未验证的 J-A `summary.json`、不得 fallback、不得网络补抓：

1. 解析 canonical project root；对 project root、`J_A_ROOT_RELATIVE_PATH` 和 `J_A_CORE_PATH` 的每一祖先拒绝 symlink，拒绝 root escape。
2. 在 import 前计算 `J_A_CORE_PATH` SHA-256，必须等于 `J_A_CORE_SHA256`。
3. import 后，`module.__file__` 与 `module.__spec__.origin` resolve 后必须都等于该 canonical source path；再次计算该 source SHA-256，仍必须相等。
4. 调用精确的 `J_A_LOADER_SYMBOL(J_A_ROOT)`；不得复制、包裹或替代 J-A reducer。
5. 再次验证四个 J-A top-level artifact 的 SHA、J-A `run_id`、J-A authority packet 中 Design/Plan/Core SHA，以及以下 projection：

| projection | frozen value |
| --- | ---: |
| catalog denominator articles | 335 |
| target parents | 131 |
| resolved parents | 125 |
| J-A `coverage_complete` parents | 118 |
| J-A parent evidence-gap parents | 13 |
| in-scope USDT children | 281 |
| archive-complete children | 278 |
| archive-gap children | 3 |

只有 exact J-A strict load 和 projection 都成立，J-B 才可读取 J-A manifest 所列的 raw ZIP、`.CHECKSUM` 与 J-A projection。J-B 不重新执行 J-A network inventory。

### 1.2 上游数据边界

J-A 的 CSV header 必须严格为：

```text
agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker
```

`transact_time` 和 `price` 是历史成交打印，不是 bid/ask、mark price、可成交价格或当时系统可见数据。J-A 不提供公告检测时间、全量 L2、fee、funding、借贷、order path 或 fill report。

---

## 2. Research Question And Frozen Boundaries

### 2.1 问题与独立单位

在完整保留 J-A 131 个 parent ledger、13 个上游 gaps 及任何 J-B gaps 的前提下，118 个 J-A `coverage_complete` parent 的 launch 后历史成交打印路径能否按固定规则被可重复描述。

一个 `source_article_id` 是一个 parent cluster，且是唯一独立单位。其 children 共享公告催化剂，只可作为 cluster 内诊断；281 条 child path 绝不能被称为 281 个独立机会。

### 2.2 不作的 claim

本阶段不计算费用、funding、spread、slippage、PnL、expectancy、Sharpe、仓位、signal、entry/exit 或 stop-loss；不将 1.5H N=3 friction receipt 外推为 2025-2026 trade 的成本模型；不作 `phenomenon_supported`、`alpha_candidate`、`falsified`、统计优势、经济优势、容量或执行可行性结论。

固定历史全集只能用于此探索描述，不能同时作为独立验证样本。结果无方向性或覆盖不足时只能降低研究优先级，不能证伪整个 event family。

### 2.3 Research status exact vocabulary

```text
research_mode = exploratory_descriptive_only
alpha_evidence_status = evidence_insufficient
phenomenon_claim = not_evaluated
statistical_edge_claim = not_evaluated
economic_edge_claim = not_evaluated
execution_feasibility_claim = not_evaluated
capital_survival_claim = not_evaluated
live_permission_claim = false
```

以上字段对每一种 J-B output state 都相同。`gross_return_bps` 是 historical trade-print descriptive field，不是 PnL。

---

## 3. Frozen Measurement And Gap Rules

### 3.1 Config SSOT

未来 Plan 只可向 `configs/base.py` 添加下列 exact constants，不得调参或在 `src/` 内写 magic number：

```python
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS = 300_000
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS = (300_000, 3_600_000, 14_400_000)
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS = 60_000
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES = 268_435_456
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = 536_870_912
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO = 64
EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES = 65_536
EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES = 67_108_864
EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES = 1_073_741_824
```

前三项是预注册 measurement rule。其余值不弱于 J-A archive admission caps，且 J-B 不保留 raw trade；64 MiB 是 J-B 三文件 receipt 的 hard output cap，不是输入 ZIP cap。

### 3.2 Physical order and numeric representation

每个 child 的 global physical trade order 是 `utc_date` 升序、随后该 ZIP CSV 中从 header 后的 1-based `physical_row_order` 升序。跨日期不得按 `agg_trade_id` 重排。

所有 price/quantity 必须由原始 UTF-8 decimal token 用 Python `Decimal` 解析；不得使用 binary `float`。每个 price/quantity 必须有限且严格大于零。所有 bps arithmetic 使用 `Decimal`，输出以 `0.00000001` quantize、`ROUND_HALF_EVEN`，然后 fixed-point decimal string（无 exponent、无多余末尾零、零写为 `"0"`）序列化。

### 3.3 Anchor, required package dates and horizons

对每个 J-A `in_scope_usdt` child：

1. 若其 parent 不是 J-A `coverage_complete`，该 child 所有 horizon 保留为 `child_horizon_evidence_gap`，`missing_reason=inherited_j_a_parent_gap`；不得删除。
2. `symbol_launch_time_ms` 必须为正 non-bool integer，否则 `missing_reason=evidence_gap_missing_launch_time`。
3. 仅在该 child 的 J-A verified physical packages 内，anchor 是 `transact_time >= symbol_launch_time_ms` 的第一条 global physical row。若无 row 或 `anchor_time_ms - symbol_launch_time_ms > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS`，所有 horizon 为 `evidence_gap_anchor_delay`。
4. 对 anchor 成功的 child 和每个 `H`，定义 `target_time_ms=anchor_time_ms+H`，`required_j_b_dates(H)` 为与闭区间 `[anchor_time_ms,target_time_ms]` 相交的全部 UTC dates，按升序列出。
5. required date 的 `(parent_article_id,symbol,utc_date,"aggTrades","futures_um")` logical package record 必须存在、其 ZIP 与 `.CHECKSUM` 必须都在 verified J-A manifest 内、且 archive record 为 `archive_verified_with_post_launch_rows`。任一 date 不满足时，此 child/horizon 为 `child_horizon_evidence_gap`、`missing_reason=evidence_gap_missing_required_archive_package`；禁止进入该 horizon trade search，禁止把它改称 `missing_horizon_trade`，禁止网络补抓。
6. 在完整 global stream 中，selected horizon row 是所有时间落在 `[target_time_ms-EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS,target_time_ms]` 的 rows 中最后一条 global physical row。因此它同时是最大 timestamp；相同 timestamp 时，最后 physical row 胜出。没有该 row 时为 `evidence_gap_missing_horizon_trade`。
7. `trade_count` 是从 selected anchor row 至 selected horizon row 的闭区间 global physical rows 数。`sampled_min_price`、`sampled_max_price` 是同一闭区间中的 Decimal min/max；相同价格不需额外 tie-break。

`required_j_b_dates` 是 anchor 后定义的，故不会把 J-A 原本未采集的次日 ZIP 误写成“市场没有 horizon trade”。当前 J-A package contract 仅覆盖 `[launch_time_ms, launch_time_ms + 4h]` 相交日期；它不自动覆盖 `[anchor_time_ms, anchor_time_ms + 4h]`。

### 3.4 Child outcomes and parent aggregation

对 `child_horizon_complete`：

```text
gross_return_bps = 10000 * (horizon_price / anchor_price - 1)
sampled_min_excursion_bps = 10000 * (sampled_min_price / anchor_price - 1)
sampled_max_excursion_bps = 10000 * (sampled_max_price / anchor_price - 1)
horizon_offset_ms = horizon_selected_time_ms - target_time_ms
```

`sampled_min_excursion_bps` / `sampled_max_excursion_bps` 取代 MAE/MFE 命名。它们只描述无方向的 lower/upper sampled trade-price excursion，不暗示 long、short、entry、exit、止损或可执行风险。

每个 parent/horizon：

```text
parent_horizon_complete
  iff parent is J-A coverage_complete
  and every J-A in-scope child is child_horizon_complete

parent_horizon_evidence_gap
  otherwise
```

对 complete parent，按 child symbol ASCII lexicographic order取得 child bps values，排序后取 simple median：奇数 `n` 取 index `n//2`；偶数 `n` 取 indexes `n//2-1` 与 `n//2` 的算术平均，再按 §3.2 quantize。该规则分别作用于 `gross_return_bps`、`sampled_min_excursion_bps`、`sampled_max_excursion_bps`。任何 child gap 都使整个 parent/horizon gap，且 `failed_child_reasons` 保留全部 `(symbol,reason)`，不进入 parent distribution。

### 3.5 Distribution and concentration

每个 horizon 使用 complete parent 的 `parent_gross_return_bps` distribution。排序按 `(Decimal value,source_article_id)`；`mean` 是算术平均并按 §3.2 quantize；`median` 使用 §3.4 simple median；`min/max` 是排序端点。分位数是 nearest-rank：对 `p in (10,25,50,75,90)`，index=`max(0,ceil(p*n/100)-1)`；`n=0` 时所有 distribution statistic 为 `null`，不是 NaN。

`top_1_abs_return_contribution` 与 `top_3_abs_return_contribution` 仅是 concentration diagnostic：分子为按 `(-abs(parent_gross_return_bps),source_article_id)` 排序的前 1 或前 3 个 absolute return 之和，分母为全部 complete parent absolute return 之和。分母为零时两者均为 canonical `"0"`。相应 parent IDs 也必须输出。不得将该指标表述为收益贡献。

---

## 4. Exact J-B Receipt Contract

### 4.1 Location, grammar and final tree

```text
OUTPUT_PARENT = data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response
RUN_ID_REGEX = ^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$
FINAL_ROOT = <OUTPUT_PARENT>/<RUN_ID>
STAGING_ROOT = <OUTPUT_PARENT>/.staging.<RUN_ID>.<decimal-pid>
SCHEMA_VERSION = stage1_5j_b_historical_aggtrades_launch_response_v1
```

`FINAL_ROOT` must be contained in the canonical project root; output parent, all ancestors and every output path must be non-symlink. The exact final regular-file membership is `manifest.json`, `summary.json`, `review_CN.md`; no directory, raw ZIP, CSV, journal, authorization file or extra regular file is allowed below final root. All JSON is canonical UTF-8 `canonical_json_dumps(...) + "\n"`; Markdown is UTF-8 with LF line endings and one final LF.

### 4.2 Exact summary schema

`summary.json` has exactly this lexicographically rendered top-level key set:

```text
analysis_state, authority_flags, authority_packet, child_horizon_rows,
child_rows, coverage_counts, decision, j_a_input, parent_horizon_rows,
research_status, run_id, schema_version
```

`j_a_input` has exactly `j_a_core_path`, `j_a_core_sha256`, `j_a_journal_sha256`, `j_a_manifest_sha256`, `j_a_root_relative_path`, `j_a_run_id`, `j_a_summary_sha256`, `j_a_review_sha256`.

`research_status` has exactly the eight §2.3 keys. `authority_flags` has exactly the twelve keys below, all literal `false`:

```text
alpha_claim_allowed, alpha_interpretation_allowed, commit_allowed,
deployment_allowed, execution_allowed, live_trading_allowed, network_allowed,
paper_trading_allowed, pnl_calculation_allowed,
receipt_generation_allowed_without_authorization, replay_allowed,
signal_generation_allowed
```

`child_rows`, ordered `(source_article_id,symbol)`, has exactly:

```text
anchor_delay_ms, anchor_price, anchor_state, anchor_time_ms,
j_a_child_state, j_a_parent_state, required_archive_dates_by_horizon,
source_article_id, symbol, symbol_launch_time_ms
```

It has exactly one row for every J-A parent-record child whose `child_scope=in_scope_usdt`; `required_archive_dates_by_horizon` is exactly a map with only `"300000"`, `"3600000"`, `"14400000"`, each mapped to an ascending, duplicate-free array of `YYYY-MM-DD` strings. Thus its frozen cardinality is 281.

`child_horizon_rows`, ordered `(source_article_id,symbol,horizon_ms)`, has exactly:

```text
child_horizon_state, gross_return_bps, horizon_ms, horizon_offset_ms,
horizon_price, horizon_selected_time_ms, horizon_target_time_ms,
missing_reason, sampled_max_excursion_bps, sampled_min_excursion_bps,
source_article_id, symbol, trade_count
```

It has exactly three rows for each `child_rows` row, one for every frozen horizon, hence 843 rows. `failed_child_reasons` is an array ordered `(symbol,missing_reason)` whose elements have exactly `missing_reason` and `symbol`.

`parent_horizon_rows`, ordered `(source_article_id,horizon_ms)`, has exactly:

```text
failed_child_reasons, horizon_ms, parent_gross_return_bps,
parent_horizon_state, parent_sampled_max_excursion_bps,
parent_sampled_min_excursion_bps, source_article_id, source_parent_state
```

It is the complete 131-parent by three-horizon Cartesian ledger, ordered as stated, hence exactly 393 rows. This includes J-A gap parents even when they have no child row.

`coverage_counts` has exactly `j_a_parent_coverage_complete_count`, `j_a_parent_coverage_gap_count`, `j_a_target_parent_count`, `n_child_horizon_complete_by_horizon`, `n_child_horizon_gap_by_horizon`, `n_parent_horizon_complete_by_horizon`, `n_parent_horizon_gap_by_horizon`, `n_parent_total`, `n_parent_with_j_a_gap`, and `parent_distribution_by_horizon`.

For each non-complete child horizon, all outcome fields (`horizon_*`, `gross_return_bps`, both excursions, `trade_count`) are `null` and `missing_reason` is one of `inherited_j_a_parent_gap`, `evidence_gap_missing_launch_time`, `evidence_gap_anchor_delay`, `evidence_gap_missing_required_archive_package`, `evidence_gap_missing_horizon_trade`. A complete child horizon has `missing_reason=null` and no null outcome field. Parent outcome fields are non-null iff `parent_horizon_complete`; gap rows retain a nonempty ordered `failed_child_reasons` and null outcome fields. Bool is never accepted where integer is required.

`parent_distribution_by_horizon` is a map keyed only by decimal-string horizons `"300000"`, `"3600000"`, `"14400000"`; each value has exactly `max`, `mean`, `median`, `min`, `n_complete_parent`, `p10`, `p25`, `p50`, `p75`, `p90`, `top_1_abs_return_contribution`, `top_1_parent_ids`, `top_3_abs_return_contribution`, `top_3_parent_ids`. Numeric statistics are canonical bps strings or null under §3.5.

`analysis_state` is `exploratory_response_described` iff all 118 frozen J-A complete parents have `parent_horizon_complete` at all three horizons; otherwise it is `exploratory_response_evidence_gap`. `decision` is respectively `stage1_5j_b_historical_aggtrades_launch_response_described_published` or `stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published`. This reducer is independent of return sign, concentration or any Alpha interpretation.

### 4.3 Authority packet, manifest and review

`authority_packet` has exactly these keys: `approved_j_b_design`, `approved_j_b_plan`, `audited_cli`, `audited_config`, `audited_core`, `j_a_manifest_sha256`, `receipt_generation_authorization`. `j_a_manifest_sha256` is exactly the lower-case 64-hex string frozen in §1.1.

Each of the first five is exactly `{relative_path,sha256}`. `receipt_generation_authorization` is exactly `{authorized_run_id,relative_path,sha256}`. It is valid only when its sidecar SHA and exact UTF-8 authorization grammar bind all seven values:

```text
APPROVED_J_B_DESIGN_SHA256
APPROVED_J_B_PLAN_SHA256
AUTHORIZED_RUN_ID
AUDITED_J_B_CORE_SHA256
AUDITED_J_B_CLI_SHA256
AUDITED_CONFIG_SHA256
J_A_MANIFEST_SHA256
```

Its canonical location is `.git/plan-execution/stage1_5j_b/<APPROVED_J_B_PLAN_SHA256>/receipt_generation_authorization.txt` and its `.sha256` sidecar. The text is exactly eight ASCII-key/value lines, in the preceding field order, each terminated by one LF; line 8 is `NETWORK_ALLOWED=false`. The first seven lines are the exact `KEY=<value>` bindings above. No whitespace, extra line, alias, shell expansion or caller-supplied path is allowed. It may be accepted only after the Design and Plan are approved and the bound Core/CLI/Config have passed their independent completion audit. It is a future, one-run, offline authority and is absent now. It grants neither network nor any downstream consumer. `Plan approval != implementation authority`; `implementation completion != receipt-generation authority`; `receipt published != downstream consumer authority`.

`manifest.json` has exactly `artifacts`, `root_relative_path`, `run_id`, `schema_version`. `artifacts` is a lexicographically ordered list by `relative_path`, with exactly `{byte_count,relative_path,sha256}` for `review_CN.md` and `summary.json`; `manifest.json` does not self-list. `root_relative_path` is the exact project-relative final root.

`review_CN.md` is solely the deterministic projection of summary: title/run ID; input identity table; authority and research-status table; coverage table; three horizon distribution tables; parent-horizon ledger in frozen row order; child and child-horizon ledgers in frozen row order; explicit gap reason legend; non-claim declaration. Renderer must use the canonical serialized strings above, fixed headings/order, no wall-clock field and no free text input. Loader must independently re-render byte-for-byte.

### 4.4 Publication, recovery and failure precedence

One `fcntl.flock(LOCK_EX)` on fixed `OUTPUT_PARENT` covers collision check through staging write, file fsync, directory fsync, atomic rename and final-parent fsync. Legal state classification is only `absent`, `staging_only`, `final_only`, `final_plus_staging`; only `absent` can start. Every non-absent state is collision STOP. No overwrite, resume, cleanup or RUN_ID reuse is allowed.

Producer and loader fail in this order: containment/symlink/regular-file violation; J-B receipt authority; exact J-A source identity; J-A strict-loader failure; J-A physical artifact/projection mismatch; ZIP/CSV structural invalidity; J-B schema/reduction/render mismatch; manifest/tree mismatch. A valid but unavailable required J-A archive package is the explicit evidence gap in §3.3, not a structural STOP. Loader accepts only `final_only`; it rejects `absent`, `staging_only`, `final_plus_staging`, any extra file and any symlink.

---

## 5. Resource Boundary And Consumer Matrix

J-B streams one verified ZIP member at a time using `ZipFile.open()` and a bounded `TextIOWrapper`/CSV iterator. It must not call `ZipFile.read()`, `extract()`, whole-file CSV read, retain raw trades, retain full child paths, or process more than one package concurrently. Its accumulator is bounded to anchor plus three horizon selectors/extrema/counts; J-B receipt stores reductions only. ZIP member size, uncompressed size and compression ratio must be checked before opening under §3.1 caps. Insufficient free disk/root-size breach is STOP, never truncation.

| role | allowed | forbidden |
| --- | --- | --- |
| J-A loader | exact strict J-A read | network, J-A mutation, permissive summary read |
| J-B producer | future authorized local reduction and atomic J-B write | network, raw retention, J-A regeneration, PnL/strategy |
| J-B loader | strict re-admission and independent recomputation | caller-controlled project root, fallback, partial root |
| future consumer | only separately authorized research Design | signal/execution/paper/live/Alpha promotion |
| auditor | read-only canonical root and `/tmp` one-mutation copies | production-root mutation, network |

`RISK_LIVE_TRADING_ENABLED` remains `False`.

---

## 6. Acceptance Invariants

| ID | Acceptance invariant |
| --- | --- |
| INV-JB-01 | Only the exact J-A root, exact J-A source/import identity and strict-loader projection in §1 can be admitted. |
| INV-JB-02 | All 131 upstream parent rows and all J-A gaps remain represented; no parent/child is omitted for outcome, symbol or density. |
| INV-JB-03 | Every anchor-dependent horizon first proves `required_j_b_dates`; unavailable J-A package is retained as `evidence_gap_missing_required_archive_package`, never inferred as no trade. |
| INV-JB-04 | Global row order, tie-breaks, Decimal arithmetic, numeric serialization, windows and trade counts are exactly §3. |
| INV-JB-05 | `source_article_id` is the only independent unit; parent aggregation is the frozen equal-child simple median and only complete parents enter distributions. |
| INV-JB-06 | All J-A and J-B gap reasons remain explicit; missing evidence never becomes negative Alpha evidence. |
| INV-JB-07 | Producer and strict loader must independently enforce the exact receipt/tree/schema/reducer/render contract in §4. |
| INV-JB-08 | Publication is parent-flocked, fsynced, atomic, no-resume and collision fail-closed; only `final_only` is consumable. |
| INV-JB-09 | Trade-print history is non-PIT descriptive evidence only; all claims stay at §2.3 and no cost/execution/Alpha result is produced. |
| INV-JB-10 | J-B receipt generation needs a separately explicit offline authority; publication grants no consumer, signal, execution, paper or live authority. |
| INV-JB-11 | Input parsing and output generation are bounded streaming under §3.1 and §5; J-B retains no raw trade archive. |
| INV-JB-12 | Positive fixtures derive from the full strict-loaded J-A root under §7; no handcrafted cross-boundary positive data is allowed. |

---

## 7. Fixture And Verification Provenance

Positive tests must begin with the full exact J-A root, run exact J-A strict loader, assert §1 projection, then derive fixtures. A cropped J-A root must never impersonate a sealed J-A root; hand-written CSV, parent/child dictionaries, authority packets and copied hashes are forbidden at the boundary.

`canonical_multi_child_complete_fixture_v1` is outcome-blind: select the lexicographically first `source_article_id` among J-A `coverage_complete` parents with at least two in-scope children for which each child has, using only header/field validity, package dates, timestamps, and physical row order, a valid anchor and three selected horizon rows under §3. Price values, returns, min/max excursion and result ranking must not be inspected for selection. The current frozen J-A projection admits the profile; the selected fixture is derived only after J-A strict load.

The Plan must also derive, from the same full root, the lexicographically first child whose `required_j_b_dates` lacks a verified J-A package if such a child exists. If it does not exist in the frozen root, a single declared mutation of the derived package-membership view is the negative fixture for `evidence_gap_missing_required_archive_package`; it must not modify a production root.

Required verification includes: exact J-A source-origin and before/after SHA negative probes; one-mutation J-A manifest/projection failures; anchor delay gap; required-date gap; missing horizon trade; same-timestamp last-row tie; complete multi-child parent median; parent gap retention; numeric/percentile/concentration exact oracle calculated outside the function under test; one mutation each of summary schema, row, reducer count, review, manifest and authority; dual-process same-RUN collision; all four lifecycle states; resource-cap rejection; public CLI canonical-entry wiring; actual pytest/Ruff/anti-shortcut RC, `git diff --check`, and `RISK_LIVE_TRADING_ENABLED is False`.

---

## 8. Future Implementation Surface And No-Touch Set

Only a later approved Plan may whitelist:

```text
configs/base.py
src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py
scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py
tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py
tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py
tests/fixtures/external_signal_shadow/stage1_5j_b/**
```

No-Touch: J-A source/root/authority bytes, frozen parser, 1.5D/F/G/H/I sources and receipts, risk/execution code, VPS state and all current permission flags. A Plan cannot invent different observation rules, fixtures, thresholds, authority grammar, receipt schema, consumer or lifecycle owner.

---

## 9. Deferred Questions

| question | owner | reason deferred |
| --- | --- | --- |
| Cost-adjusted economic edge | separate economic/execution Design | no fees, L2, fills or funding evidence in J-B. |
| Generalizable phenomenon/statistical inference | preregistered independent-validation Design | this is one fixed historical exploratory cohort. |
| Repair of 13 J-A gaps | separate provenance Design | J-B cannot reopen J-A network capture. |

No deferred item changes this Design's deterministic descriptive reducer.

---

## 10. Review Packet And Routing

### 10.1 Minimal external J-A evidence packet for independent review

The reviewer must receive the exact bytes of: the final J-A Receipt Closure Audit report that positive-loads `J_A_RUN_ID` and records its semantic mutations; J-A `manifest.json`, `summary.json`, `review_CN.md`, `request_journal.jsonl`; and `J_A_CORE_PATH`. If the Closure Audit report independently binds all raw manifest membership, the 703 raw input files/ZIPs need not be uploaded. Existing J-A Design/Plan may be supplied for chain context but do not substitute for the root and closure-audit packet.

### 10.2 Routing

With the §10.1 packet absent: `EVIDENCE_GAP`, no Plan. With it present, Model B performs `closure_confirmation` over only P0-01..07/P1-01..04 and their frozen proof edges. A recommendation to approve this Design still does not authorize implementation, receipt generation, network, strategy replay, consumer access, paper trading or live trading.
