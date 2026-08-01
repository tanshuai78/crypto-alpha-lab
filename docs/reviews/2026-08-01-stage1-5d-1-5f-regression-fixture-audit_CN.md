# Stage 1.5D/1.5F Regression Fixture 建议

## Scope
- evidence_sources:
  - `_project_context/server_evidence/20260801_grvt_title_gate/` (Live Server Runtime Evidence)
  - `tests/fixtures/external_signal_shadow/stage1_5d/` (Stage 1.5D Parser & Collector Local Fixtures)
  - `tests/fixtures/external_signal_shadow/stage1_5f/` (Stage 1.5F Observer Local Fixtures)
  - `docs/designs/` & `docs/reviews/` (Design Specifications & Retrospective Reviews)
- synced_from_server: Targeted evidence package `20260801_grvt_title_gate` containing `grvt_events_hits.jsonl`, `grvt_rejected_hits.jsonl`, `exchangeinfo_grvt_snapshot.json`, `observer_state.jsonl`, `watermark.json`, and `detail_retry_scheduler_state.json`.
- local_fixture_paths_checked:
  - `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json`
  - `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_f434_real_frozen_fixture.json`
  - `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_d0833_fixture.json`
  - `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_6cbb_fixture.json`
  - `tests/fixtures/external_signal_shadow/stage1_5d/binance_futures_launch_fixture.json`
  - `tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl`

## Fixture Candidates
以下针对关键历史事件与事故样本进行 Fixture 分类与审计。按数据来源类型划分为：`real_frozen_bapi_payload`（真实冻结 BAPI 响应 Payload）、`server_runtime_evidence`（服务器运行现场日志与快照）及 `synthetic_offline_fixture`（人工离线构造测试 Fixture）：

| fixture_id | article_id | symbol_set | incident | source_files_available | missing_files | data_quality | should_freeze |
|---|---|---|---|---|---|---|---|
| `grvt_title_bypass_incident` | `20536b05b2a34b87a3bae99c45d0dc91` | GRVTUSDT | Title 单 Symbol 旁路导致未抓取正文开盘时间，并在上线前（提前 75 分钟）被 1.5F 直通 `exchangeInfo` 误杀判定为 `symbol_not_in_exchangeinfo` 硬拒绝。 | `server_runtime_evidence`: `grvt_events_hits.jsonl`, `grvt_rejected_hits.jsonl`, `exchangeinfo_grvt_snapshot.json`, `observer_state.jsonl` | `real_frozen_bapi_payload`: 缺少 `20536b...` 对应的真实 BAPI 详情正文 Payload（因 1.5D 当时跳过了详情请求）。 | **High** (运行时日志完整，缺少原始 BAPI 正文) | **MUST FREEZE**: 必须冻结为 1.5D/1.5F 核心回归 Fixture，防范 Title 快路径直通发射漏洞。 |
| `pypl_multisymbol_batch` | `93b5cd2280874d9cb4303827374b940d` | PYPLUSDT, GSUSDT, SMHUSDT | 多 Symbol 显式标题全员 Batch 准入与交错开盘（Staggered Launch）推进验证。 | `docs/designs/2026-07-29-...` 规约文本、`test_run_stage1_5f_live_depth_observer.py` 测试用例 | `real_frozen_bapi_payload`: 缺少该文章原始 BAPI 详情 Payload。 | **Medium** (已有合成集成测试用例) | **SHOULD FREEZE**: 建议冻结真实 BAPI 响应以替换测试用例中的 Mock。 |
| `a827_tradfi_table_parser` | `a827177a387e4ebea830110ba222ca48` | TMFUSDT, TBTUSDT, BITOUSDT | 泛化标题 `Multiple TradFi...` 依赖 40KB+ BAPI 详情 HTML `<table>` 逐行解析 Symbol 与开盘时间点。 | `real_frozen_bapi_payload`: `bapi_article_detail_a827_real_frozen_fixture.json` (103KB) | 无 | **High** (已完整冻结本地真实 Payload) | **FROZEN**: 已冻结为解析器核心回归测试 Fixture。 |
| `popmart_advance_pub` | `fcdc949b45a644c78e341c88331a35ef` | POPMARTUSDT | 单 Symbol 提前发布，上线前挂起与空盘口观察窗口。 | `data/external_signal_shadow/stage1_5a/` 历史记录 | `real_frozen_bapi_payload`: 缺少原始 BAPI 详情 Payload。 | **Medium** (已有日志记录) | **SHOULD FREEZE**: 冻结为提前发布空盘口处理回归测试。 |
| `f434_tradfi_202_starvation` | `f43403ef11974998bc0f46420826577a` | SHAZUSDT, SOFIUSDT, PANWUSDT, PENGUSDT | BAPI 详情页持续返回 HTTP 202 / 空 Body 导致重试调度饥饿与降级。 | `real_frozen_bapi_payload`: `bapi_article_detail_f434_real_frozen_fixture.json` & `bapi_article_detail_f434_fixture.json` | 无 | **High** (已完整冻结) | **FROZEN**: 已冻结为 Retry Scheduler 饥饿降级回归测试。 |
| `d0833_degraded_endpoint` | `d0833e4ae9b542be90dbf3fe1c960c53` | GEVUSDT, VRTUSDT, SNOWUSDT, APPUSDT | Detail 接口服务降级退回（Degraded Endpoint Fallback）。 | `synthetic_offline_fixture`: `bapi_article_detail_d0833_fixture.json` | 无 | **High** (已冻结) | **FROZEN**: 已冻结为端点降级退回回归测试。 |
| `6cbb_non_usdt_settlement` | `6cbb1b11a9c843949624cf2eacaac8b4` | SPCXUSD1 | 非 USDT 结算资产后缀（`USD1`）合约 Symbol 匹配。 | `synthetic_offline_fixture`: `bapi_article_detail_6cbb_fixture.json` | 无 | **High** (已冻结) | **FROZEN**: 已冻结为结算资产正则扩展测试。 |
| `f598_historical_hygiene` | `f598c7bb87d74b8c995b9f67bf210be1` | NFLXUSDT, AMZNUSDT, GOOGUSDT | 历史 Anchor 终端拒绝数据清理 Hygiene。 | `synthetic_offline_fixture`: `malformed_historical_rejected_rows.jsonl` | 无 | **High** (已冻结) | **FROZEN**: 已冻结为历史拒绝状态 Hygiene 测试。 |

## Required Fixtures

为确保系统重构与回归测试不依赖真实线上新事件等待，必须在 codebase 中冻结以下 4 个标准契约 Fixtures：

| fixture_name | source_article_id | expected_symbols | expected_launch_times_utc | expected_stage1_5d_behavior | expected_stage1_5f_behavior |
|---|---|---|---|---|---|
| `bapi_article_detail_grvt_real_frozen_fixture.json` | `20536b05b2a34b87a3bae99c45d0dc91` | GRVTUSDT | 2026-07-31 12:45:00 UTC | **禁止走快路径直接 Emit**。必须强制发起 BAPI 详情页抓取，解析正文中的开盘时间锚点（`12:45:00 UTC`），并将开盘时间塞入 `symbol_effective_launch_times_ms` 后方可发射。 | 接收到 GRVTUSDT 事件后，识别到 `detected_at_ms` (11:32 UTC) 早于开盘时间锚点 (12:45 UTC)，**禁止立即向 exchangeInfo 校验并 Hard Reject**；保持 `pending_launch_time_in_future` 状态，直至 12:45 UTC 时再次校验 exchangeInfo 并在交易对上架后晋升为 Active 启动深度观察。 |
| `bapi_article_detail_pypl_real_frozen_fixture.json` | `93b5cd2280874d9cb4303827374b940d` | PYPLUSDT, GSUSDT, SMHUSDT | 2026-07-29 11:00:00 UTC | 标题解析提取 3 个 Symbol，生成 Unified Batch ID，发起 BAPI 正文抓取验证开盘时间点，输出完整的 Multi-Symbol Candidate Event。 | 注册 `event_batch_registry`。按三者各自的开盘时间点分别推进；在三者均达到 Durable/Active 之前，全局 Watermark 禁止跨越该批次。 |
| `bapi_article_detail_a827_real_frozen_fixture.json` | `a827177a387e4ebea830110ba222ca48` | TMFUSDT, TBTUSDT, BITOUSDT | 2026-07-27 10:00:00 UTC | 标题无 Symbol。通过 40KB+ HTML `<table>` 解析器成功提取 3 个 Symbol 及其开盘时间戳，发射带 Anchor 的 Candidate Event。 | 依据提取的时间戳实施挂起与准入；校验完整后开启深度观测。 |
| `bapi_article_detail_fcdc_real_frozen_fixture.json` | `fcdc949b45a644c78e341c88331a35ef` | POPMARTUSDT | 2026-07-23 09:00:00 UTC | 单 Symbol 提前发布。提取正文开盘时间，正确输出带有 9:00 UTC 开盘锚点的事件。 | 在 9:00 UTC 前保持 Pending，9:00 UTC 开盘时若盘口盘深较薄，正确记录 `insufficient_depth` 诊断日志而非异常崩溃。 |

## Minimal Raw Evidence Still Missing

**严格拒绝全量同步线上 `data/` 目录**。仅针对关键验证缺失的**最小单一原始 Payload** 进行精细补全：

| article_id | required_server_path / URL | local_target_path | reason |
|---|---|---|---|
| `20536b05b2a34b87a3bae99c45d0dc91` | `https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=20536b05b2a34b87a3bae99c45d0dc91` | `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_grvt_real_frozen_fixture.json` | 线上事故发生时，Stage 1.5D 误跳过了 BAPI 详情请求，导致线上 `raw_payloads/` 目录缺乏该文章的原始 BAPI Detail Payload。补齐该单一 JSON Payload 是验证正文开盘时间解析与消除 Title 旁路漏洞的最小依赖。 |
| `93b5cd2280874d9cb4303827374b940d` | `https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=93b5cd2280874d9cb4303827374b940d` | `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_pypl_real_frozen_fixture.json` | 当前多 Symbol 批次测试使用 Mock 临时拼装，缺乏真实多 Symbol 公告的 HTML/JSON 原始结构。补全此单一文章即可覆盖显式标题多 Symbol 正文结构。 |

## Test Coverage Matrix

| fixture | bug_class | existing_test | missing_test |
|---|---|---|---|
| `bapi_article_detail_grvt_real_frozen_fixture.json` & `exchangeinfo_grvt_snapshot.json` | Title Fast-Path Bypass & Premature ExchangeInfo Hard Rejection | `test_run_stage1_5d_live_event_source_smoke_collector.py` 中仅有通用 Title 匹配测试；Stage 1.5F 中仅有已知开盘时间测试。 | **Missing**: 1) 验证 1.5D 收到 GRVT 标题公告后**必须发起 Detail Fetch**，禁止输出 `detail_fetch_status="not_needed"`；<br>2) 验证 1.5F 收到 GRVT 事件后，在 11:32 UTC（早于 12:45 UTC）时**禁止判定 `symbol_not_in_exchangeinfo` 硬拒绝**，必须置为 `pending_launch_time_in_future`。 |
| `bapi_article_detail_pypl_real_frozen_fixture.json` | Multi-Symbol Batch Watermark Staggered Promotion | `test_three_staggered_symbols_promote_at_their_own_anchor` (使用 Mock Data) | **Missing**: 使用真实冻结的 PYPL BAPI Payload 验证 1.5D 批次发射与 1.5F 水印单次提交行为。 |
| `bapi_article_detail_a827_real_frozen_fixture.json` | HTML Table Line Schedule Parser Drift | `test_stage1_5d_live_event_source_parser.py` (包含 `a827` 提取测试) | 覆盖已完备。 |
| `bapi_article_detail_f434_real_frozen_fixture.json` | Detail Endpoint HTTP 202 Retry Starvation | `test_bapi_existing_f434_d0833_6cbb_fixtures_still_pass` | 覆盖已完备。 |
| `bapi_article_detail_6cbb_fixture.json` | Settlement Asset Regex Exclusion (`USD1`) | `test_stage1_5d_live_event_source_parser.py` (包含 `6cbb` 测试) | 覆盖已完备。 |

## Conclusions
- must_add_fixtures:
  1. **`bapi_article_detail_grvt_real_frozen_fixture.json`**: 从 Binance BAPI 拉取文章 `20536b05b2a34b87a3bae99c45d0dc91` 的真实正文 Payload 并冻结在 `tests/fixtures/external_signal_shadow/stage1_5d/`。
  2. **GRVT GRVTUSDT 提前发布 1.5F 准入测试 Fixture**: 将 `_project_context/server_evidence/20260801_grvt_title_gate/` 中的 `grvt_events_hits.jsonl` 与 `exchangeinfo_grvt_snapshot.json` 引入测试套件，用作 1.5F 开盘前挂起（No Premature Hard Reject）回归测试的输入。

- optional_fixtures:
  1. **`bapi_article_detail_pypl_real_frozen_fixture.json`**: 冻结 `93b5cd2280874d9cb4303827374b940d` 的真实正文，增强多 Symbol 批次测试的真实度。
  2. **`bapi_article_detail_fcdc_real_frozen_fixture.json`**: 冻结 `fcdc949b45a644c78e341c88331a35ef` (POPMART) 真实正文。

- fixtures_not_needed:
  - **严禁全量同步服务器 `data/` 目录**：`data/` 下数十 GB 的历史行情与日志切片无需合入 Git 仓库。所有回归校验均必须基于小巧（< 200KB）且确定性的单文章 JSON/JSONL Fixtures。
