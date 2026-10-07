# Stage 1.5J-A Historical Archive Coverage Inventory Design

**日期:** 2026-10-05
**状态:** `draft_for_independent_closure_review`
**范围:** Binance USD-M USDT-margined perpetual-launch announcement universe 与 daily `aggTrades` archive coverage inventory
**实现、网络、VPS、SSH、deployment、receipt generation、replay、execution、paper、live 许可:** `false`
**研究 claim level:** `evidence_insufficient`

---

## 1. 目的、事实与边界

J-A 不做历史回放、收益、成本覆盖或 Alpha 判断。它只在一个独立、单次、显式授权的 public-read-only run 中回答：固定十二个完整 UTC 月的 Binance announcement catalog 中，哪些 article 是 USD-M perpetual launch parent；每个由公告 detail 明确声明的 child，launch 后四小时对应的 daily USD-M `aggTrades` ZIP 是否能以同路径 `.CHECKSUM` 验证、严格解析并留下 coverage evidence。

### 1.1 已确认事实

1. 1.5G/H/I receipt 是范围受限的本地 evidence；不构成历史 announcement denominator，也不授予 J-A 网络、回放、价格或 Alpha 权限。
2. Frozen parser [stage1_5d_live_event_source_parser.py](../../src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py) 的 SHA-256 为 `7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5`。J-A 只允许调用其 `classify_event_type()` 和 `extract_symbol_candidates_from_bapi_article_payload()`；不得复制、替代、patch 或选择其他 parser。
3. 该 parser 可识别 `USDT`、`USDC` 与 `USD1` child。J-A 的研究 scope 仅覆盖 suffix 为 `USDT` 的 child；其他 parser-declared child 仍必须被保留和解释，不能静默删除。
4. [Binance public-data README](https://github.com/binance/binance-public-data) 将 USD-M Futures daily `aggTrades` 与同路径 checksum 作为公开 archive 约定。该 archive 是事后历史数据，不证明系统在事件当时收到过它，也不提供 order book、fee、funding、成交或 PnL 证据。

### 1.2 固定 universe 与非目标

```text
UNIVERSE_START_MS = 1759276800000  # 2025-10-01T00:00:00.000Z
UNIVERSE_END_MS   = 1790812800000  # 2026-10-01T00:00:00.000Z, exclusive
PRESENCE_WINDOW_MS = 14400000      # launch 后四小时，仅决定 archive package
```

- Parent 的分组单位是 `source_article_id`；一个 article 的 children 不是独立统计样本。
- In-window catalog article 永远保留在 denominator，即使不是 launch、detail 缺失、detail 不可解析、或 archive 缺失。
- J-A 不读取、修改或重跑 1.5D/F/G/H/I、1.6 或 VPS collector；不计算 price、return、MAE/MFE、PnL、费用、funding、slippage、expectancy、signal、entry/exit、Kill/Promote。
- 任何 archive gap 都是 `evidence_gap`，绝不是 negative Alpha evidence。

---

## 2. Revision authority、blocker ledger 与 scope

本修订遵循已冻结的 closure-audit graph。Review finding 只能在当前 source、parent invariant 与权限边界兼容时被采纳。

| Finding | Impact cone / restored invariant | disposition |
| --- | --- | --- |
| P0-01 | one-time network authority -> request admission -> staging | 闭合为 exact packet、sidecar、code/config binding 与 one-use collision rule |
| P0-02 | BAPI bytes -> parser -> parent identity | 闭合为 parser SHA/entrypoint 与 detail envelope binding |
| P0-03 | parser-declared children -> USDT reducer -> archive URL | 闭合为全 child projection 和 suffix partition |
| P0-04 | catalog pages -> deterministic target-parent selection -> denominator | 闭合为 title-bound two-pass stable scan、selector、cross-page order 与 sentinel |
| P0-05 | request admission -> raw response -> crash/recovery | 闭合为 fsynced append-only journal 的单一状态机 |
| P0-06 | reducer -> summary/manifest/review -> strict loader | 闭合为 exact schemas、state enums、membership/count formulas、state precedence与 render contract |
| P0-07 | real raw inputs -> TDD -> production | 已冻结真实 GRVT 四段 source chain、canonical fixture manifest 与 parser projection；后续 fixture materialization 必须逐字节匹配 Section 8，不能伪装或重抓 |
| P1-01 | ZIP/checksum processing -> resource safety | 闭合为 compressed/uncompressed/checksum caps 与 streaming-only rule |

**Mutable Set:** 本文件的 Sections 3-9，以及直接对应的 acceptance/verification edges。
**No-Touch Set:** approved/upstream Design、`configs/base.py` current bytes、frozen parser bytes、all 1.5D/F/G/H/I/1.6 code and receipts、execution/risk configuration、VPS/runtime state。
**Allowed future implementation files only:**

```text
configs/base.py
src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py
scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py
tests/research/external_signal_shadow/test_stage1_5j_a_historical_archive_coverage_inventory.py
tests/scripts/external_signal_shadow/test_run_stage1_5j_a_historical_archive_coverage_inventory.py
tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/**  # only the exact Section 8 bytes
```

No other file, permission, lifecycle owner, downstream consumer or public production entrypoint is authorized by this Design.

---

## 3. Authority packet and request admission

### 3.1 Exact one-time network authorization

After implementation has passed a fresh Completion Audit, the sole canonical authorization locator is:

```text
.git/plan-execution/stage1_5j_a/<APPROVED_PLAN_SHA256>/
  network_authorization.txt
  network_authorization.sha256
```

Both paths must be regular non-symlink files, project-contained after ancestor checks. The sidecar bytes are exactly `<lowercase-64-hex>  network_authorization.txt\n`; its digest must equal the text bytes. The text has exactly these newline-terminated lines, in this order, no blank, duplicate or extra lines:

```text
APPROVED_DESIGN_SHA256=<64-lower-hex>
APPROVED_PLAN_SHA256=<64-lower-hex>
AUTHORIZED_RUN_ID=stage1_5j_a_historical_archive_coverage_inventory_<UTC-YYYYMMDDTHHMMSSZ>
APPROVED_J_A_CORE_SHA256=<64-lower-hex>
APPROVED_J_A_CLI_SHA256=<64-lower-hex>
APPROVED_CONFIG_SHA256=<64-lower-hex>
APPROVED_PARSER_SHA256=7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5
NETWORK_PROFILE_ID=stage1_5j_a_public_archive_inventory_v1
CATALOG_PAGE_LIMIT_PER_PASS=50
MAX_CATALOG_REQUESTS=100
MAX_DETAIL_REQUESTS=200
MAX_ARCHIVE_REQUESTS=800
```

Before creating staging, resolving DNS or opening any HTTP connection, `run_inventory(run_id)` must validate the exact grammar and bind every hash to the actual approved Design/Plan/core/CLI/config/parser bytes. The core and CLI hashes must be the exact bytes independently completion-audited for this Plan. Any missing, changed, mismatched or reused packet is `STOP=stage1_5j_a_network_authorization_mismatch`.

`NETWORK_PROFILE_ID` resolves only to this document's Sections 3.2 and 5.3: the exact URL grammars, all request/byte caps and the exact all-false authority-flag key set. It may not select an alternate capability profile or relax any flag.

The only public production entrypoint is `run_inventory(run_id)`. It takes no root, URL, page, symbol, output or authority-bundle argument. Under the common parent lock it creates the run-specific staging directory immediately after authority validation; existing final or staging for the authorized `RUN_ID` is fatal. Therefore an authorization that has reached staging cannot be reused, resumed or redirected. A new attempt needs a newly authorized `RUN_ID` and packet.

### 3.2 Fixed source grammar and caps

The authorization permits only HTTPS `GET`, port 443, no redirect, cookie, credential, fragment or request body, against:

| kind | exact URL grammar |
| --- | --- |
| catalog | `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=<positive-int>&pageSize=50` |
| detail | `https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=<32-lower-hex>` |
| archive | `https://data.binance.vision/data/futures/um/daily/aggTrades/<SYMBOL>/<SYMBOL>-aggTrades-<YYYY-MM-DD>.zip` |
| checksum | the exact archive URL plus `.CHECKSUM` |

`<SYMBOL>` must be an exact uppercase parser-declared `USDT` child; archive URLs have no query. Any nonmatching URL, cap exceedance or request after terminal journal state is `STOP=stage1_5j_a_request_admission_failure`.

New J-A-only `configs/base.py` SSOTs are:

```text
EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_SIZE = 50
EXTERNAL_SIGNAL_STAGE1_5J_A_CATALOG_PAGE_LIMIT_PER_PASS = 50
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CATALOG_REQUESTS = 100
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_DETAIL_REQUESTS = 200
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_REQUESTS = 800
EXTERNAL_SIGNAL_STAGE1_5J_A_HTTP_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_BAPI_RESPONSE_BYTES = 2097152
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_ZIP_BYTES = 268435456
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_CHECKSUM_RESPONSE_BYTES = 16384
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = 536870912
EXTERNAL_SIGNAL_STAGE1_5J_A_MAX_ARCHIVE_COMPRESSION_RATIO = 64
EXTERNAL_SIGNAL_STAGE1_5J_A_ROOT_MAX_BYTES = 8589934592
EXTERNAL_SIGNAL_STAGE1_5J_A_ROOT_ORDINARY_RESERVE_BYTES = 1073741824
EXTERNAL_SIGNAL_STAGE1_5J_A_NETWORK_RETRY_COUNT = 0
```

`MAX_ARCHIVE_REQUESTS` counts ZIP plus checksum requests together. ZIP member `ZipInfo.file_size` and compression ratio are checked before opening; implementation streams exactly one approved member with `ZipFile.open()` and a byte counter, never `ZipFile.read()`, never `extract()`, and stops at either resource cap.

---

## 4. Catalog, detail and child reduction

### 4.1 Stable two-pass catalog denominator

Persist raw catalog bytes before parsing. **Scan A** requests pages 1 through its first valid pre-window sentinel page. **Scan B** immediately requests pages 1 through that same page number. Each page is valid only if its rows have unique 32-lower-hex `code`, non-bool integer `releaseDate`, string `title`, and non-increasing release dates. The raw catalog `code` is the exact `catalog_source_article_id`; it is never rewritten or inferred from a detail request parameter.

For each scan, the final row of page N must have `releaseDate >=` the first row of page N+1. Scan A may end only after a row has `releaseDate < UNIVERSE_START_MS`; Scan B must contain a pre-window row on that same sentinel page. The ordered tuple sequence `(pageNo, code, releaseDate, title)` must be byte-for-byte equivalent between scans through the sentinel. Any parsing failure, repeated code, cross-page inversion, tuple difference, unavailable page or no sentinel is `STOP=stage1_5j_a_catalog_completeness_unproven` and publishes nothing.

All rows with `UNIVERSE_START_MS <= releaseDate < UNIVERSE_END_MS` become `catalog_denominator_records`, before target selection. For each row, `catalog_event_type = classify_event_type(exact_catalog_title)` using the frozen parser. If and only if it equals frozen `EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE` (`futures_contract_launch`), the row is a target candidate and its detail request is mandatory. Otherwise `candidate_status=not_target_event_type` and `detail_request_id=null`. A target candidate is never demoted to `not_target_event_type`: it becomes `catalog_detail_unresolved` unless its bound detail title independently classifies to the same primary event type and all detail requirements pass; only then is it `resolved_target_parent`. Neither archive availability nor later relevance changes membership.

### 4.2 Detail envelope and frozen parser

For every target candidate, request `articleCode=<catalog_row.code>`. `articleCode` is the detail URL query parameter, not a catalog JSON field. A persisted detail response is usable only when:

```text
top-level key set == ["code", "data", "message", "messageDetail", "success"]
code == "000000"
success == true
data is an object
data.code == requested detail URL articleCode == catalog_row.code == catalog_source_article_id
data.title is a string
data.body is a string
```

The exact raw JSON bytes, SHA-256 and request id are retained. `classify_event_type(data.title)` must equal the catalog selector's frozen `EXTERNAL_SIGNAL_STAGE1_5D_PRIMARY_EVENT_TYPE` (`futures_contract_launch`) before the detail is a target parent. A valid envelope whose detail title differs from the catalog selector is `catalog_detail_unresolved`, never `not_target_event_type`. `extract_symbol_candidates_from_bapi_article_payload(payload, title=data.title)` must return `symbol_validation_status="validated_by_exact_text"`, a nonempty duplicate-free symbol list, and a positive non-bool integer launch time for every declared child. Any detail failure retains the target candidate as `catalog_detail_unresolved`; no archive URL is formed.

### 4.3 Full child projection and USDT partition

Every successfully parsed detail child is retained in original parser list order with:

```text
symbol, symbol_launch_time_ms, child_scope
```

`child_scope` is `in_scope_usdt` iff `symbol.endswith("USDT")`; otherwise it is `out_of_scope_non_usdt`. The complete detail must parse before a parent resolves. A mixed parent therefore retains its USDC/USD1 children but constructs packages only for `in_scope_usdt`; all non-USDT children have no archive request ids and are never counted as missing archive coverage. No USDT target announcement may disappear from the denominator.

For an in-scope child, intersecting UTC dates of `[launch_time_ms, launch_time_ms + PRESENCE_WINDOW_MS]` produce one logical record each. Its physical archive identity is `(symbol, utc_date, "aggTrades", "futures_um")`; logical identity adds `parent_article_id`. A physical package may serve multiple logical records but is fetched once. Repeated logical identity is fatal.

---

## 5. Durable journal, archive validation and publication

### 5.1 Append-only request journal

The staging root contains `request_journal.jsonl`, excluded only from no-file checks by being explicitly listed in the manifest. For every admitted request the writer append+fsyncs an intent record **before** DNS/HTTP, then append+fsyncs exactly one terminal record.

```text
intent exact keys:  event, request_id, request_kind, request_state, url, parent_article_id, symbol, utc_date
terminal exact keys: event, request_id, request_state, http_status, transport_error, response_relative_path, response_sha256, response_bytes
```

The intent is exactly `event="request_intent"` and `request_state="admitted_pending"`. The terminal is exactly `event="request_terminal"` and its `request_state` is exactly one of `response_persisted`, `http_not_found`, `transport_inconclusive`, `response_rejected`; there is no second terminal-state authority. `request_id` is a one-based contiguous integer. Intent identity fields are null only where irrelevant to the request kind. Terminal combinations are fixed:

```text
response_persisted:       http_status=200, transport_error=null, all response_* non-null and response_bytes>0
http_not_found:           http_status=404, transport_error=null, all response_*=null
transport_inconclusive:  http_status=null, transport_error=nonempty string, all response_*=null
response_rejected:        http_status=non-bool integer other than 200 or 404, transport_error=null, all response_*=null
```

A persisted raw file is atomically written and fsynced before its terminal line. The final receipt is forbidden if an intent lacks one terminal, has more than one terminal, ids are not contiguous/unique, total requests exceed caps, or a terminal record is incoherent with raw bytes. The summary `request_records[].request_state` is exactly the matching terminal `request_state`; a final receipt contains no `admitted_pending` projection.

No resume occurs after any crash: a staging root is nonconsumable, retains the journal for inspection, and blocks its `RUN_ID`.

### 5.2 Package verification and descriptive reducer

A persisted ZIP/checksum pair is verified only if same-path checksum grammar names the exact ZIP basename and its digest equals ZIP bytes; both raw files are regular, non-symlink and staging-contained. ZIP has exactly one regular member named `<SYMBOL>-aggTrades-<YYYY-MM-DD>.csv`, no traversal, duplicate, symlink or unexpected member. The CSV header is exactly `agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker`; rows have seven fields, nondecreasing positive millisecond timestamps, finite positive decimal price/quantity, non-bool nonnegative integer ids, and lowercase `true|false` maker flag. Invalid schema is fatal, not filtered.

The reducer streams verified rows by `(utc_date,row_order)` and emits only `post_launch_row_count`, `first_post_launch_trade_time_ms`, `last_post_launch_trade_time_ms`, and `first_post_launch_trade_delay_ms`. Zero rows is `archive_observation_gap`, not a market or trading claim.

### 5.3 Sealed tree, schemas and state reducer

The final root is exactly:

```text
data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/
  stage1_5j_a_historical_archive_coverage_inventory_<RUN_ID>/
```

It contains precisely `request_journal.jsonl`, `raw/catalog_scan_a/<pageNo>.json`, `raw/catalog_scan_b/<pageNo>.json`, `raw/article_details/<article_id>.json`, `raw/archive/<symbol>/<utc_date>.zip`, its `.CHECKSUM`, summary, review and manifest; no other file, directory or symlink is allowed. A raw response exists iff the journal has its matching `response_persisted` terminal event.

Canonical JSON is UTF-8, no BOM, sorted object keys, `,`/`:` separators, newline terminated. Arrays are ordered as stated below. Every SHA-256 is lowercase 64-hex; every count/id/timestamp is a non-bool integer; nullable fields are explicitly `null` only where listed.

**Summary exact top-level keys:**

```text
analysis_state, archive_package_records, authority_flags, authority_packet,
catalog_denominator_records, catalog_scan, coverage_inventory, decision,
parent_records, request_records, run_id, schema_version, universe_window
```

`schema_version` is `stage1_5j_a_historical_archive_coverage_inventory_v1`. `universe_window` has exactly `end_exclusive_ms,start_ms`. `catalog_scan` has exactly `page_limit_per_pass,scan_a_page_count,scan_b_page_count,sentinel_page_no,stable_tuple_sha256`. `authority_packet` has exactly `approved_design,approved_plan,audited_cli,audited_config,audited_core,frozen_parser,network_authorization`; each nested object has exactly `relative_path,sha256`, except `network_authorization`, which additionally has `authorized_run_id,network_profile_id`.

`catalog_denominator_records`, ordered `(release_date_ms,source_article_id)`, each have exactly `candidate_status,detail_request_id,release_date_ms,source_article_id,title`. `candidate_status` is exactly `not_target_event_type`, `catalog_detail_unresolved` or `resolved_target_parent`; `detail_request_id` is null iff status is `not_target_event_type`.

`parent_records`, ordered by `source_article_id`, have exactly one row for each catalog target candidate and exactly `children,detail_payload_sha256,detail_request_id,detail_status,parent_state,source_article_id`. `detail_status` is exactly one of `validated_target_detail`, `detail_nonpersisted`, `detail_title_disagreement`, `detail_parser_unresolved`; `parent_state` is exactly one of `coverage_complete`, `coverage_evidence_gap_detail`, `coverage_evidence_gap_no_in_scope_usdt_child`, `coverage_evidence_gap_archive`. `children` preserves parser order and each row has exactly `child_scope,symbol,symbol_launch_time_ms`. A `validated_target_detail` has non-null raw/detail fields and is the only detail status permitted to have children. `detail_nonpersisted` has null `detail_payload_sha256`; `detail_title_disagreement` and `detail_parser_unresolved` have the persisted detail SHA-256; all three have no children and `parent_state=coverage_evidence_gap_detail`. A bad detail envelope/identity is a terminal STOP, not a parent-record enum value.

`archive_package_records`, ordered `(parent_article_id,symbol,utc_date)`, each have exactly `checksum_request_id,child_state,first_post_launch_trade_delay_ms,first_post_launch_trade_time_ms,last_post_launch_trade_time_ms,logical_archive_identity,parent_article_id,post_launch_row_count,symbol,utc_date,zip_request_id`. `child_state` is exactly `archive_verified_with_post_launch_rows`, `archive_verified_zero_post_launch_rows` or `archive_request_nonpersisted`. The four trade fields are non-null only for `archive_verified_with_post_launch_rows`; `archive_verified_zero_post_launch_rows` has `post_launch_row_count=0` and null timestamps/delay; `archive_request_nonpersisted` has all four fields null. A persisted package that fails checksum/ZIP/CSV validation is terminal STOP, not an enum value. `logical_archive_identity` has exactly `market,metric,parent_article_id,symbol,utc_date`.

`request_records` is the deterministic completed-journal projection, ordered request id, with exactly `http_status_or_transport_error,request_id,request_kind,request_state,response_bytes,response_relative_path,response_sha256,url`; `http_status_or_transport_error` is the terminal HTTP integer for all non-transport states and the terminal nonempty error string for `transport_inconclusive`; response fields follow the journal's fixed state combinations. `coverage_inventory` has exactly `catalog_denominator_count,child_coverage_complete_count,child_coverage_gap_count,in_scope_usdt_child_count,out_of_scope_child_count,parent_coverage_complete_count,parent_coverage_gap_count,resolved_parent_count,target_parent_count`, with these exact formulas:

```text
catalog_denominator_count = len(catalog_denominator_records)
target_parent_count = count(candidate_status != "not_target_event_type")
resolved_parent_count = count(candidate_status == "resolved_target_parent")
in_scope_usdt_child_count = count(children where child_scope == "in_scope_usdt")
out_of_scope_child_count = count(children where child_scope == "out_of_scope_non_usdt")
child_coverage_complete_count = count(unique (parent_article_id, symbol) where every required
  utc_date package has child_state == "archive_verified_with_post_launch_rows")
child_coverage_gap_count = in_scope_usdt_child_count - child_coverage_complete_count
parent_coverage_complete_count = count(parent_state == "coverage_complete")
parent_coverage_gap_count = target_parent_count - parent_coverage_complete_count
```

For a `validated_target_detail`, `parent_state=coverage_complete` iff it has at least one in-scope child and every one is child-coverage complete; it is `coverage_evidence_gap_no_in_scope_usdt_child` iff it has none, otherwise `coverage_evidence_gap_archive`. `authority_flags` has only these exact boolean-false keys:

```text
alpha_claim_allowed, alpha_interpretation_allowed, commit_allowed,
deployment_allowed, execution_allowed, live_trading_allowed,
network_allowed_after_run, paper_trading_allowed, pnl_calculation_allowed,
price_response_calculation_allowed, receipt_generation_allowed_without_authorization,
replay_allowed, signal_generation_allowed
```

The manifest has exactly `artifacts,root_relative_path,run_id,schema_version`; `artifacts` lists every regular final-root file except the manifest itself in lexicographic relative-path order. Each entry has exactly `byte_count,relative_path,sha256`. The strict loader requires exact tree membership, recomputes journal projection, parser-derived parent/child mapping, logical/physical package references, all coverage counts, summary canonical bytes, manifest entries and all authority flags.

`review_CN.md` is non-authoritative but must equal the UTF-8 output of `render_stage1_5j_a_review(summary)`: exactly a title line, `run_id`, `analysis_state`, `decision`, universe bounds, catalog counts, parent table (`source_article_id,parent_state,child counts`), archive table (`parent_article_id,symbol,utc_date,child_state,post_launch_row_count`), coverage counts, and false-authority table, each in summary array order. The loader regenerates and byte-compares it.

State precedence is fixed: authority/catalog/detail-envelope/identity/checksum/ZIP-or-CSV-schema/journal/lock/manifest failure -> `STOP` and no publication; otherwise any `parent_state != "coverage_complete"` -> `coverage_inventory_evidence_gap` / `stage1_5j_a_historical_archive_coverage_evidence_gap_published`; otherwise -> `coverage_inventory_complete` / `stage1_5j_a_historical_archive_coverage_inventory_published`. The strict loader requires `parent_coverage_gap_count == count(parent_state != "coverage_complete")` and permits `coverage_inventory_complete` iff `parent_coverage_gap_count == 0`. No failed row can be removed before this reduction.

Publication holds one `fcntl.flock(LOCK_EX)` on the fixed output-parent directory from collision check through staging, all fsyncs, rename and parent-directory fsync. Summary/review/manifest are written last and re-read/hash-checked before atomic rename. Staging is never loader-consumable.

---

## 6. Acceptance invariants

| ID | Invariant |
| --- | --- |
| INV-15J-A-01 | Two stable, ordered catalog scans and the pre-window sentinel establish the fixed denominator; archive discoverability cannot alter it. |
| INV-15J-A-02 | Every in-window row and every parser-declared child has a retained, deterministic status. |
| INV-15J-A-03 | Detail binding is `catalog_row.code == requested detail URL articleCode == data.code == catalog_source_article_id`; only frozen parser entrypoints derive child/schedule. |
| INV-15J-A-04 | Only `in_scope_usdt` children form daily `aggTrades` URL identities; non-USDT children remain visible but are not archive gaps. |
| INV-15J-A-05 | Every request has a durable intent then one durable terminal journal record before receipt reduction. |
| INV-15J-A-06 | ZIP, same-path checksum, CSV grammar and bounded streaming validation are required before row facts are usable. |
| INV-15J-A-07 | Exact schema/tree/reducer/render recomputation prevents a self-consistent producer/loader pair from redefining the receipt. |
| INV-15J-A-08 | Complete requires every required in-scope child; all omissions remain `evidence_gap`. |
| INV-15J-A-09 | Only completion-audited bytes plus one exact, run-bound authorization may issue public requests; no alternate writer exists. |
| INV-15J-A-10 | J-A makes no PIT, price, cost, PnL, Alpha, execution, paper/live or downstream-consumer claim. |

---

## 7. Verification and negative probes

Required Plan gates: Task 0 frozen baseline/index/scope and source hashes; canonical fixture derivation; focused tests; `ruff check`; `RISK_LIVE_TRADING_ENABLED is False`; actual `anti_shortcut_scan.py` process RC `0`; independent code review; fresh Completion Audit. Tests never authorize network I/O.

### 7.1 Pre-network implementation and Completion Audit

Section 8's exact GRVT packet is a canonical component fixture, not a valid complete J-A receipt root: it does not contain two complete stable catalog scans or their pre-window sentinel. Before the separately authorized production network run, positive proof may therefore cover only the exact fixture's parser, package/checksum/ZIP/CSV validator, reducer, renderer and private lifecycle writer path. It must not rename, relabel, synthesize or infer missing catalog pages, and it must not claim a full-root strict-loader positive load.

The strict loader must be implemented in this phase. It may be given malformed or incomplete roots only to prove fail-closed structural behavior; those probes do not prove the full-root semantic gates and do not discharge §7.2. Required pre-network probes use exactly one mutation unless the state transition inherently needs a crash:

1. missing/wrong authority line, sidecar, code/config hash or reused RUN_ID -> authority STOP before staging/DNS/HTTP;
2. wrong `data.code`, top-level detail envelope or parser source origin/hash -> detail identity STOP;
3. mixed USDT/USDC/USD1 detail -> full projection retained; only USDT gets archive URL;
4. cross-page ordering fault or a Scan A/B change to any `(pageNo, code, releaseDate, title)` projection field -> catalog STOP;
5. crash between admitted intent and terminal response -> nonconsumable staging and no final receipt;
6. mismatched checksum, bad ZIP member/header/timestamp, compression expansion or response cap -> package STOP/gap according to the invariant;
7. zero valid post-launch rows -> retained `coverage_inventory_evidence_gap` row;
8. two processes same RUN_ID -> only one passes the common parent lock; the other collision-stops.

### 7.2 Post-network receipt closure audit

After one separately authorized production network run creates the first complete physical J-A receipt root, the strict receipt closure audit must first positive-load that exact root. Only a byte-identical copy of this positive-loaded root may be used as the baseline for one-at-a-time semantic mutations. The audit must mutate and, after any required manifest recomputation, prove the exact intended strict-loader STOP for: summary, review, enum, count formula, denominator or parent omission, duplicate journal terminal, and authority packet. An always-reject loader is not sufficient evidence because it cannot satisfy the required positive load.

Failure to complete this closure audit leaves the produced root unavailable as verified evidence for any future consumer. This is an audit timing rule only: it creates no new receipt schema or state, and grants no network, Alpha, replay, execution, paper or live authority.

---

## 8. Pre-implementation canonical input fixture: frozen capture binding

P0-07 is closed only for the exact already captured GRVT packet below. The capture source is `tmp/stage1_5j_a_canonical_fixture_capture/`; it is revision evidence, not a J-A receipt, runtime input or production output. A future Task 0 may materialize only byte-identical copies under `tests/fixtures/external_signal_shadow/stage1_5j_a/canonical_input_v1/`; it may not rename, regenerate, refresh, select a replacement packet or call the network.

```text
catalog_page_2.json
  byte_count = 52973
  sha256 = 2da6a1f5b80c82f2cd1ece1ca3fa3465a74f5bfe267d467ae93677b4825bd6b2
article_detail_20536b05b2a34b87a3bae99c45d0dc91.json
  byte_count = 72478
  sha256 = c5d400781f7b94309131ee04adb8a617998d56a8f28e53407deaa80061e94ccd
GRVTUSDT-aggTrades-2026-07-31.zip
  byte_count = 1891845
  sha256 = 6c6d2cf12075006f4999cfda6fb5a0cd0217c67a01971977d8737de19e834a85
GRVTUSDT-aggTrades-2026-07-31.zip.CHECKSUM
  byte_count = 100
  sha256 = 6267ba25e6f12d7b09d3c064b60f1caf61fdf01c9165544f22ddc258ccc52b48
fixture_manifest.json
  byte_count = 1239
  sha256 = 2dd1e5c3cea9080ec0bee91c746f29339e31daf60d083b7b9598d59188fbcfd1
```

The canonical manifest is UTF-8 without BOM, sorted object keys, `,`/`:` separators and one trailing newline. It has exactly `article_code,archive_url,catalog_url,checksum_url,detail_url,files,fixture_schema_version`; every `files` row has exactly `relative_path,sha256,byte_count`. Its exact identities are:

```text
catalog_url = https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=2&pageSize=50
catalog_row.code = 20536b05b2a34b87a3bae99c45d0dc91
detail_url = https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=20536b05b2a34b87a3bae99c45d0dc91
detail.data.code = 20536b05b2a34b87a3bae99c45d0dc91
parser child = GRVTUSDT
parser launch_time_ms = 1785501900000
archive_url = https://data.binance.vision/data/futures/um/daily/aggTrades/GRVTUSDT/GRVTUSDT-aggTrades-2026-07-31.zip
checksum_url = archive_url + .CHECKSUM
```

The raw catalog identity is `code`, not `articleCode`; `articleCode` appears only as the detail URL parameter. The adjacent checksum's declared ZIP SHA-256 must equal the ZIP's exact bytes. Task 0 must independently parse the captured catalog/detail using the frozen parser, recompute all five byte counts and SHA-256 values, and reject any additional, missing, renamed or mismatched fixture file with `STOP=stage1_5j_a_canonical_fixture_mismatch`. The J-A core/CLI may not create, refresh or substitute this fixture. This is a hard positive-fixture provenance gate, not a reason to use mocked success responses.

---

## 9. L2, safety and routing

This is a deterministic data-coverage claim only. `coverage_inventory_complete` means the declared data checks passed, not `phenomenon_supported`, `alpha_candidate`, `falsified`, economic edge or execution feasibility. Later research needs a separately approved Design for hypothesis, parent-level sample treatment, PIT semantics, price/trade construction, cost evidence, hold/risk rules and independent validation.

```text
Design closure review
  -> Design approval -> Plan -> Task 0 exact fixture materialization/verification
  -> implementation/tests -> pre-network Completion Audit
  -> separate one-time production network authorization -> one inventory run
  -> strict receipt closure audit: positive-load first complete root, then semantic mutation suite
  -> only closure-audited receipt bytes may be treated as verified by a future consumer
```

`RISK_LIVE_TRADING_ENABLED` remains `False`. No Design/Plan/test/review/receipt grants commit, push, deployment, SSH, replay, signal, execution, paper or live authority.
