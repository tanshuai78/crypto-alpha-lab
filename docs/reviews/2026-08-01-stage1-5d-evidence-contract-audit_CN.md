# Stage 1.5D Evidence Contract 审计

## Scope
- files_reviewed:
  - `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
  - `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
  - `src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py`
  - `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
  - `configs/base.py`
  - `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
  - `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- commit_or_snapshot: `feature/external-signal-shadow-stage1` (2026-08-01 Workspace HEAD) & Live Server Evidence Snapshot (`_project_context/server_evidence/20260801_grvt_title_gate/`)
- audit_focus: 审计 Stage 1.5D 所有写入 `events/*.jsonl` 的代码分支与数据路径，排查是否存在绕过 launch-time / exchangeInfo 校验的事件发射（emit）路径，重点复盘 `GRVTUSDT` 事故路径（Title 解析 Symbol -> `detail_fetch_status=not_needed` -> 直接 Emit -> Stage 1.5F 上线前误杀 Hard Reject）。

## Event Emit Paths
在 `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` 中，共有 **13 处代码分支** 调用 `append_jsonl(stream_paths["events"], norm_event)` 将事件写入 `events/*.jsonl`。各路径触发条件与风险审计如下：

| path_id | file/function | trigger_condition | symbol_source | requires_detail | requires_exchangeinfo | requires_launch_anchor | can_emit_without_anchor | risk |
|---|---|---|---|---|---|---|---|---|
| **Path 1 (GRVT 事故路径)** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1166-L1182) | 轮询 RSS/BAPI 文章列表时，标题中直接正则提取到 Symbol（`ev.get("symbols")` 非空，如 `GRVTUSDT`）。 | `title` | **False** (`detail_fetch_status="not_needed"`) | **False** | **False** (`symbol_effective_launch_times_ms={}`) | **True** | **CRITICAL**: 标题含 Symbol 即直接写入 `events/*.jsonl`，完全绕过 BAPI 正文抓取与上线时间解析。若公告提前发布（如 GRVT 提前 75 分钟），Stage 1.5F 会在开盘前查询 exchangeInfo 失败并触发永久 Hard Reject。 |
| **Path 2** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1400-L1420) | BAPI Detail 接口抓取成功，从 HTML/JSON 正文中解析提取到 Symbol 列表。 | `bapi_article_body` / `detail` | **True** | **False** | **Partial** (解析 `symbol_launch_times_ms`，若文本未匹配到时间则为空) | **True** | **MEDIUM**: 依赖正文解析。若正文中仅有 Symbol 但无格式化上线时间，仍会发射无 Anchor 事件。 |
| **Path 3** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1450-L1470) | Detail 抓取失败或返回空 Payload，退回到 Candidate Set 或标题派生提取。 | `title_contract_symbol` / `title_base_asset_derived` | **Attempted** (尝试但失败) | **False** | **False** | **True** | **HIGH**: 正文降级兜底路径，缺失上线时间锚点。 |
| **Path 4** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1550-L1570) | Detail 抓取未返回正文 Symbol，退回到标题合约 Candidate 提取。 | `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **HIGH**: 标题合约 Candidate 兜底发射，缺乏 launch_time。 |
| **Path 5** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1610-L1630) | Detail Retry 重试循环中提取到标题 Candidate 并发射。 | `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **HIGH**: 重试兜底发射。 |
| **Path 6** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1730-L1750) | Detail Retry 重试队列中文章达到 Max-Age (3600s) 超时，在硬拒绝前发射 Fallback Candidate。 | `title_contract_symbol` / `title_base_asset_derived` | **Attempted/Timed out** | **False** | **False** | **True** | **HIGH**: Max-Age 超时降级发射，缺乏开盘时间校验。 |
| **Path 7** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L1980-L2000) | Pending Detail 重试队列第二轮循环中命中 Candidate 发射。 | `detail` / `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **MEDIUM**: 异步重试发射。 |
| **Path 8** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2120-L2140) | Deferred Detail 重试队列中延迟发起的 Candidate 发射。 | `detail` / `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **MEDIUM**: 延迟重试发射。 |
| **Path 9** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2370-L2390) | Scheduled Detail 定时重试成功并提取到 Candidate 发射。 | `detail` | **True** | **False** | **Partial** | **True** | **LOW**: 正常定时重试成功路径。 |
| **Path 10** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2430-L2450) | Detail Retry 响应解析成功并提取到候选 Symbol 发射。 | `detail` | **True** | **False** | **Partial** | **True** | **LOW**: 正常重试解析路径。 |
| **Path 11** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2470-L2490) | Detail Retry 降级回退 Candidate 发射。 | `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **HIGH**: 降级回退发射。 |
| **Path 12** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2520-L2540) | Detail Retry 提取标题 Symbol 发射。 | `title` | **Attempted** | **False** | **False** | **True** | **HIGH**: 标题 Symbol 兜底发射。 |
| **Path 13** | `run_stage1_5d_live_event_source_smoke_collector.py` / `main()` (L2600-L2620) | 轮询末尾清理队列中遗留 Candidate 发射。 | `title_contract_symbol` | **Attempted** | **False** | **False** | **True** | **MEDIUM**: 末尾清理发射。 |

## Contract Violations

| severity | file | function | condition | observed_gap | expected_contract | recommended_test |
|---|---|---|---|---|---|---|
| **CRITICAL** | `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | `main()` (L1166-L1182) | 标题提取到 Symbol（`ev.get("symbols")` 非空） | 代码在 L1166 执行 `if ev.get("symbols"):` 后，直接调用 `normalize_live_event` 生成事件并写入 `events/*.jsonl`。它自动将 `detail_fetch_status` 设为 `not_needed`，跳过 BAPI 详情正文抓取，导致事件的 `symbol_effective_launch_times_ms` 为空。没有任何 launch_time 或 exchangeInfo 校验。 | 单 Symbol 标题公告**不得**跳过 BAPI 详情正文抓取。必须请求 BAPI 详情页以解析精确开盘时间（`symbol_effective_launch_times_ms`）；若详情页不可用，事件必须被标记为 `launch_anchor_required=True`，禁止直通发射。 | `test_single_symbol_title_must_fetch_body_or_flag_launch_anchor` |
| **HIGH** | `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | `main()` (L1730-L1750) | Detail Retry 达到 Max-Age (3600s) 超时降级 | 超时降级发射的 Candidate Event 缺乏上线时间校验，未在事件元数据中明确标识 `launch_time_unverified=True`，导致 Stage 1.5F 依然按照即时交易对存在性（exchangeInfo）进行判定。 | 所有降级/无时间锚点发射的 Candidate Event，必须明确标注 `launch_time_unverified=True`，强制 Stage 1.5F 延迟校验。 | `test_max_age_expiry_fallback_metadata_contract` |
| **MEDIUM** | `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py` | `extract_symbol_candidates_from_title` (L514-L545) | 单 Symbol 标题 vs 多 Symbol 标题解析契约不一致 | `extract_symbol_candidates_from_title` 在单 Symbol 时直接返回 `symbol_extraction_source="title"`，而多 Symbol 标题（如 `Multiple TradFi...`）会触发 Batch 创建并进入 BAPI 正文解析队列。单 Symbol 与多 Symbol 证据契约严重不对等。 | 单 Symbol 与多 Symbol 必须遵循一致的证据契约（Evidence Contract Parity）：均须抓取正文解析上线时间表，统一生成 Batch/Anchor 元数据。 | `test_single_and_multi_symbol_evidence_contract_parity` |

## GRVT Incident Mapping

根据服务器现场证据 `_project_context/server_evidence/20260801_grvt_title_gate/`，GRVTUSDT 事故的完整链路复盘如下：

| step | observed_evidence | code_path | expected_behavior |
|---|---|---|---|
| **1. 公告发布** | Binance 于 `2026-07-31 11:30:11 UTC` 发布公告 `Binance Futures Will Launch USDⓈ-Margined GRVTUSDT Perpetual Contract (2026-07-31)`。Binance `exchangeInfo` 中记录该合约实际 `onboardDate` 为 `2026-07-31 12:45:00 UTC`（公告发布比开盘提前 75 分钟）。 | Binance RSS/BAPI 公告源 | 交易所常态提前发布上线公告。系统应识别提前发布，并记录开盘时间锚点为 `12:45:00 UTC`。 |
| **2. 1.5D 抓取与解析** | `grvt_events_hits.jsonl`: `detected_at_ms=1785497559218` (`11:32:39 UTC`)。Title 包含 `GRVTUSDT`。代码进入 L1166 `if ev.get("symbols"):` 分支。 | `run_stage1_5d_live_event_source_smoke_collector.py` Line 1166 | 系统检测到 Title 含有 Symbol，但不应直接假定 `detail_fetch_status="not_needed"`。 |
| **3. 1.5D 无锚点发射** | `grvt_events_hits.jsonl` 中记录: `symbol_extraction_source="title"`, `detail_fetch_attempted=false`, `detail_fetch_status="not_needed"`, `symbol_effective_launch_times_ms={}`。事件于 11:32:39 UTC 被直接写入 `events/2026-07-31.jsonl`。 | `run_stage1_5d_live_event_source_smoke_collector.py` Line 1181 (`append_jsonl`) & `stage1_5d_live_event_source_parser.py` Line 270 | 1.5D 应发起 BAPI 详情抓取提取 12:45 UTC 上线时间，或输出包含上线时间锚点的 Candidate Event。 |
| **4. 1.5F 提前消费与校验** | `grvt_rejected_hits.jsonl`: 1.5F 于 `1785497616617` (`11:33:36 UTC`) 读取该事件。由于事件缺乏 launch_time，1.5F 立即向 Binance 发起 `exchangeInfo` 查询。 | `run_stage1_5f_live_depth_observer.py` Section 6.2 & `stage1_5f_live_depth_observer_loader.py` | 1.5F 识别到合约尚未到 12:45 UTC 开盘时间，应进入 `pending_launch_time_in_future` 挂起等待，而非立即校验 exchangeInfo。 |
| **5. 1.5F 致命误杀 (Hard Reject)** | 由于 11:33 UTC 时 GRVTUSDT 尚未开盘（12:45 UTC 才开盘），Binance `exchangeInfo` 查无此币。1.5F 立即将 `status` 设为 `rejected`，`rejected_reason="symbol_not_in_exchangeinfo"`，写入 `events_rejected/20260731.jsonl`。 | `stage1_5f_live_depth_observer_loader.py` | 禁止在开盘时间之前对缺少 exchangeInfo 的合约进行 Hard Reject。 |
| **6. 正式开盘失效** | `2026-07-31 12:45:00 UTC`，GRVTUSDT 在 Binance 正式开盘交易。由于 1.5F 已在 11:33 UTC 将其置为 Terminal Rejected 状态，系统无法重新 Admission，深度观察与交易信号彻底错过。 | `run_stage1_5f_live_depth_observer.py` | 12:45 UTC 到达时，1.5F 应将 Pending 状态的 GRVTUSDT 晋升为 Active 并启动深度观察。 |

## Required Invariants
- `invariant_1`: **强制正文抓取与上线时间解析（Mandatory Detail Fetch for Title Symbols）**：任何从 Title 中直接提取到的单 Symbol 上线公告，绝对禁止直接标记 `detail_fetch_status="not_needed"` 并无锚点发射；必须强制请求 BAPI 详情页解析 `symbol_effective_launch_times_ms`。
- `invariant_2`: **发射事件必带开盘时间或未验证标识（Launch Schedule Provenance）**：所有写入 `events/*.jsonl` 的 Candidate Event，必须显式包含解析出的 `symbol_effective_launch_times_ms`；若正文无法获取上线时间，必须携带 `launch_time_unverified=True` 元数据标识。
- `invariant_3`: **开盘前禁止依据 ExchangeInfo 缺失硬拒绝（No Premature Hard Rejection Before Launch Anchor）**：Stage 1.5F 在收到上线事件后，若当前系统时间早于 parsed launch_time 或事件被标记为 `launch_time_unverified=True`，绝对禁止在 `exchangeInfo` 中查无 Symbol 时直接触发 `symbol_not_in_exchangeinfo` 永久 Hard Reject，必须保持 `pending` 挂起直至开盘时间锚点到达。

## Suggested Tests

| test_name | fixture | expected_behavior |
|---|---|---|
| `test_single_symbol_title_must_fetch_body_or_flag_launch_anchor` | `tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json` | 验证当 Title 包含 `GRVTUSDT` 时，Stage 1.5D 不会直接发射 `detail_fetch_status="not_needed"` 的无时间戳事件，而是发起 BAPI 详情抓取。 |
| `test_grvt_advance_publication_no_premature_rejection` | `_project_context/server_evidence/20260801_grvt_title_gate/stage1_5d/events_hits/grvt_events_hits.jsonl` & `exchangeinfo_grvt_snapshot.json` | 模拟在 11:32 UTC 消费 GRVTUSDT 事件，验证 Stage 1.5F 将其保持在 `pending_launch_time_in_future` 状态，直至 12:45 UTC 才会查询 exchangeInfo 并晋升为 Active。 |
| `test_single_and_multi_symbol_evidence_contract_parity` | `bapi_article_detail_a827_real_frozen_fixture.json` & `bapi_article_detail_f434_real_frozen_fixture.json` | 验证单 Symbol 公告（如 GRVT）与多 Symbol 泛化标题公告（如 TradFi a827）在 Stage 1.5D 中输出完全对等的证据字段（`symbol_effective_launch_times_ms`, `detail_fetch_status`, `parser_version`）。 |

## Conclusions
- must_fix:
  1. **修补 `run_stage1_5d_live_event_source_smoke_collector.py` L1166 标题直通发射漏洞**：取消单 Symbol 标题匹配直接跳过 BAPI 详情抓取的逻辑。标题解析出 Symbol 后，必须将文章送入 BAPI 详情抓取流程，提取 `symbol_effective_launch_times_ms` 后方可发射。
  2. **修补 Stage 1.5F 开盘前误杀逻辑**：修改 `stage1_5f_live_depth_observer_loader.py` 中对 `symbol_not_in_exchangeinfo` 的拒绝判定。对于开盘时间在未来或开盘时间未知的事件，首次 exchangeInfo 查询未命中时必须置为 `pending_launch_time_in_future` 或 `pending_launch_anchor_missing`，禁止直接写入 `events_rejected/*.jsonl`。

- should_fix:
  1. **统一单/多 Symbol 证据契约（Contract Parity）**：重构 `extract_symbol_candidates_from_title` 与 `normalize_live_event`，使所有上线事件均具备标准化 Batch ID 与上线时间锚点。
  2. **完善降级发射元数据**：对于 Detail Retry 达到 Max-Age 超时降级发射的 Candidate Event，统一注入 `launch_time_unverified=True`，确保下游 Stage 1.5F 采取保守延迟校验策略。

- not_in_scope:
  - **实盘交易执行与风控参数变更**：本审计仅针对 Stage 1.5D / 1.5F 的事件发射契约与准入安全校验，`configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED = False` 保持不变，不影响任何底层实盘执行引擎。
