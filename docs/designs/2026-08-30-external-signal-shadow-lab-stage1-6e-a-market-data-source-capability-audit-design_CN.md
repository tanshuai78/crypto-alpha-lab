# External Signal Shadow Lab Stage 1.6E-A Market-Data Source Capability Audit Design

**日期:** 2026-08-30
**状态:** `design_draft`
**Review Mode:** `closure_confirmation`
**适用阶段:** Stage 1.6E-A, Binance USD-M public market-data source capability audit
**实现计划许可:** `false`
**代码实施许可:** `false`
**部署许可:** `false`

**审计记录:** 首次 Closure Audit 已完成；本次为 Closure Confirmation。`earlier_closure_audit_miss=true`；已记录遗漏为 E-A operational thresholds 的 `configs/base.py` SSOT、ProfileCore nested serialized representation、primitive token grammar、response reducer mapping、response/durability reducer separation 与 complete terminal-intent serialization mapping。`closure_escape_count=5`。

---

## 0. Frozen Authority

本草案只消费下列精确 bytes。Plan 不得替换版本；hash 改变即重新审核。

### Normative authorities

```text
2026-08-24-stage1-6-futures-delisting-route-map_CN.md
5e405d0b72f787af3c70d0799c77ce3b9b88827ec84e377a8da5928bbb8d3862

2026-08-18-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
ec2518a1e5309fb67cbecc04281b1c72044587e63a3b002514eff7036f12dfe3
```

### Operational compatibility authorities

这些文件不提供 event semantic input；它们只约束 VPS、shared-lock、storage admission 和现有 1.6D 的共存边界。

```text
2026-08-19-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md
83aaa473a9ddb287ee916eae4da327966daa7b0afd5c465f7cc883a06e4f6bc0

2026-08-25-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md
5070644d57e789ebf9c422e5a9022c58c8a606c1074cab7b849abc22f61bf202
```

## 1. Purpose, Scope, And Non-Goals

E-A performs exactly one bounded public-readonly capability probe for each of four fixed Binance USD-M REST profiles. It proves only that the named request, from the named production environment, produced a durably recorded response matching the frozen profile at that time.

```text
scope = public_market_data_source_capability_audit
production_capability_probe_location = same approved network execution environment
  as the current Stage 1.6D runtime and any future Stage 1.6E-B runtime
max_profiles = 4
max_network_requests_per_root = 4
network_mode = sequential_public_get_only
retry_policy = no_retry
probe_symbol = BTCUSDT
HTTP_TIMEOUT_SEC = 10.0
MAX_RAW_PAYLOAD_BYTES = 2_000_000
```

本地运行只允许 synthetic fixture、unit test 或 parser test；不得声称本地 capability pass 证明 VPS capability。E-A 不探测、记录或声称证明固定 public NAT IP。若未来 E-B 更换 approved host、filesystem、network namespace 或 proxy policy，必须先在新环境重新运行获批的 E-A，不得复用旧 E-A pass。

真实 probe 前的环境证明分为无网络 preflight 与正式 root revalidation 两步：

1. **Step A, VPS environment preflight:** 不创建 capability root，不请求 Binance，只将下列 projection 输出至部署授权 transcript：`deployment_host_identity`、`hostname`、`project_root_realpath`、`capability_root_parent_filesystem_st_dev`、`shared_lock_filesystem_st_dev`、`network_namespace_inode`、`proxy_environment`、`runtime_user_uid`、`deployment_git_commit`、`deployment_runtime_worktree_clean`。其中 `capability_root_parent_filesystem_st_dev = os.stat(capability_audits_parent).st_dev`，且该 parent 必须已存在。
2. **Step B, authorized capability run:** 用户的单独 VPS runtime/deployment authorization 绑定 Step A 的 exact projection。仅在授权后才创建 fresh capability root；任何网络请求前重新计算同一字段、要求它们与 Step A 相同，并要求 `os.stat(capability_root).st_dev == capability_root_parent_filesystem_st_dev == os.stat(shared_lock_path).st_dev`。随后写入并 read-back `execution_environment_attestation.json`。

`execution_environment_attestation.json` 是 first-party control artifact，exact key set 为：

```text
schema_version = stage1_6e_a_execution_environment_attestation_v1
deployment_host_identity = SHA256(Path("/etc/machine-id").read_bytes())
hostname = socket.gethostname()
project_root_realpath = str(PROJECT_ROOT.resolve(strict=True))
root_filesystem_st_dev = os.stat(capability_root).st_dev
shared_lock_filesystem_st_dev = os.stat(shared_lock_path).st_dev
network_namespace_inode = os.stat("/proc/self/ns/net").st_ino
proxy_environment = absent
runtime_user_uid = os.geteuid()
deployment_git_commit = full 40-character lowercase output of
  git rev-parse --verify HEAD^{commit}
deployment_runtime_worktree_clean = true
execution_environment_id
permissions
```

`proxy_environment=absent` requires `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `http_proxy`, `https_proxy`, `all_proxy`, `Authorization`, and `Cookie` to be absent from the request environment. `deployment_runtime_worktree_clean=true` requires all of: `git diff --quiet -- configs src scripts`; `git diff --cached --quiet -- configs src scripts`; and `git ls-files --others --exclude-standard -- configs src scripts` returns no path. `execution_environment_id = SHA256(UTF8(canonical_json(attestation with only execution_environment_id omitted)))`. This attestation proves the approved local host/filesystem/network-namespace/proxy-policy environment without a fifth external request; it does not prove an external NAT address.

The separate VPS runtime/deployment authorization must name this attested environment before a real probe. Future E-B must write the same attestation schema and fail closed unless its `deployment_host_identity`, `project_root_realpath`, both filesystem identities, network namespace and proxy policy equal the approved E-A evidence. This comparison consumes no 1.6D root, checkpoint or source payload.

E-A 不读取、等待、订阅或消费任何 1.6D root、checkpoint、terminal 或 sealed export；不接收公告、symbol、semantic trigger 或 revision；不形成 PIT、event coverage、historical retention、净成本、收益、replay、alpha 或交易结论。

`fee` 不在 E-A scope：

```text
fee_profile_status = not_in_scope
fee_coverage_status = not_evaluated_in_stage1_6e_a
net_cost_or_profit_claim_allowed = false
```

## 2. Confirmed Boundaries And Permissions

1. 1.6D 只产生 source observation/DetailRevision，不产生 `system_available_at_ms` 或 `fact_available_at_ms`；E-A 不创建其替代物。
2. 现有 1.6A real-capture semantic consumer 未获批；E-A 不模拟或替代它。
3. `historical_backfill` 和任何 sealed export 不能产生 E-A PIT evidence，且不是 E-A 输入。
4. `public_rest_visible_orderbook` 是普通 public depth 可见订单簿，不声称完整 L2 或完整市场流动性。
5. Stage 1.5D/F/G/H 与 1.6D 的 runtime/root/artifact 不是 E-A 数据输入或输出；同机 storage coordination 不是数据依赖。

所有 **E-A first-party semantic/control artifacts** 必须含下列 exact permissions object：`execution_environment_attestation`、`source_profile_attestations`、`capability_observations`、`capability_summary`、`terminal_status`、`manifest`。`raw` exact response bytes 与 canonical `ProfileCore` 不注入这些字段。

```text
RISK_LIVE_TRADING_ENABLED = false
execution_feasibility_claim_allowed = false
net_cost_or_profit_claim_allowed = false
replay_allowed = false
alpha_interpretation_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
private_api_allowed = false
authenticated_api_allowed = false
order_api_allowed = false
```

## 3. Fixed ProfileCore Contract

`BTCUSDT` 只是不带事件含义的 bootstrap symbol。每份 `source_profiles/<profile_id>.json` 是 exact `ProfileCore` canonical UTF-8 JSON bytes，且不包含 attestation hash、run ID、时间或 permissions。

所有 ProfileCore 共有：

```text
exact_keys =
  profile_schema_version
  market_source_profile_id
  market_data_subtype
  method
  scheme
  host
  path
  canonical_query
  expected_response_schema
  payload_time_semantics
  parser_version
  max_raw_response_bytes
  public_readonly
  documented_request_weight
  documented_rate_limit_scope
  rate_limit_documentation_observed_at
  extra_fields_policy
profile_schema_version = stage1_6e_a_profile_core_v1
method = GET
scheme = https
host = fapi.binance.com
public_readonly = true
parser_version = stage1_6e_a_profile_parser_v1
max_raw_response_bytes = 2_000_000
extra_fields_policy = allowed
```

`canonical_query` 使用 key 的 lexical ascending order，无 URL fragment、body、authorization 或 cookie。所有 ProfileCore top-level 与 nested object 的 JSON type 和 token grammar 均由本节唯一确定；Plan 不得新增 type、token 或 representation。

```text
integer = JSON integer where type(value) is int; JSON bool is forbidden
ms_timestamp = integer >= 0
decimal_string = JSON string matching ASCII regex
  ^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$
  ("-0" is permitted; "+", exponent, NaN, Infinity, whitespace and leading zeros are rejected)
literal_BTCUSDT = exact JSON string "BTCUSDT"
enum_Regular_Special = exact JSON string "Regular" or "Special"
price_quantity_tuple_array = JSON array, possibly empty; every item is a JSON array
  of exact length 2 and both elements satisfy decimal_string
documented_request_weight = integer >= 0 | exact JSON string "not_stated"
rate_limit_documentation_observed_at = ASCII JSON string YYYY-MM-DD accepted by
  datetime.date.fromisoformat
```

All fixed ProfileCore scalar fields are JSON strings except `max_raw_response_bytes` (`integer`), `public_readonly` (exact JSON `true`) and `documented_request_weight` (the union above). `expected_response_schema` and `payload_time_semantics` are JSON objects defined below. Extra response field does not constitute drift; a missing required field, root/type error, token error, enum error or tuple-grammar error is `profile_schema_drift`.

| Profile ID | Subtype | Path and canonical query | Root/schema and payload-time contract | Documented request metadata |
|---|---|---|---|---|
| `binance_usdm_rest_depth_v1` | `public_rest_visible_orderbook` | `/fapi/v1/depth`; `limit=100&symbol=BTCUSDT` | root `object`; required `lastUpdateId: integer`, `E: ms_timestamp` (server output time), `T: ms_timestamp` (transaction time), `bids`/`asks`: array`; every entry is exactly `[price_decimal_string, quantity_decimal_string]`; E-A records both times but does not infer event time. | `documented_request_weight=5`; `documented_rate_limit_scope=endpoint_documented_weight`; docs observed `2026-08-31` |
| `binance_usdm_rest_premium_index_v1` | `mark_price` | `/fapi/v1/premiumIndex`; `symbol=BTCUSDT` | root `object`; required `symbol: "BTCUSDT"`, `markPrice`, `indexPrice`, `estimatedSettlePrice`, `lastFundingRate`, `interestRate`: decimal strings; `nextFundingTime`, `time`: ms timestamps. `time` is payload observation time, not event time. | `documented_request_weight=1`; `documented_rate_limit_scope=endpoint_documented_weight`; docs observed `2026-08-31` |
| `binance_usdm_rest_funding_rate_v1` | `funding_realized_history` | `/fapi/v1/fundingRate`; `limit=1&symbol=BTCUSDT` | root `array` with exactly one object; required `symbol: "BTCUSDT"`, `fundingRate`, `markPrice`: decimal strings, `fundingTime: ms_timestamp`, `rateType: Regular\|Special`. `fundingTime` is realized funding event time, not request observation time. | `documented_request_weight=not_stated`; `documented_rate_limit_scope=shared_500_requests_per_5_minutes_per_IP_with_fundingInfo`; docs observed `2026-08-31` |
| `binance_usdm_rest_open_interest_hist_5m_v1` | `oi_historical_period_5m` | `/futures/data/openInterestHist`; `limit=1&period=5m&symbol=BTCUSDT` | root `array` with exactly one object; required `symbol: "BTCUSDT"`, `sumOpenInterest`, `sumOpenInterestValue`: decimal strings, `timestamp: ms_timestamp`. `timestamp` is the 5-minute period end time, not request observation time. | `documented_request_weight=0`; `documented_rate_limit_scope=endpoint_documented_weight`; docs observed `2026-08-31` |

`expected_response_schema` and `payload_time_semantics` are not prose fields. They have the following exact JSON grammar inside ProfileCore. `required_fields` applies to the root object when `root_type="object"`, and to the sole root-array object when `root_type="array"`.

```text
expected_response_schema exact keys =
  root_type
  root_array
  required_fields
  tuple_array_fields

root_array = null | {"exact_length": 1, "item_type": "object"}
tuple_array_fields = object whose values are exactly
  ["price_decimal_string", "quantity_decimal_string"]
```

The four exact ProfileCore nested values are:

```json
{
  "binance_usdm_rest_depth_v1": {
    "expected_response_schema": {
      "root_type": "object",
      "root_array": null,
      "required_fields": {
        "E": "ms_timestamp",
        "T": "ms_timestamp",
        "asks": "price_quantity_tuple_array",
        "bids": "price_quantity_tuple_array",
        "lastUpdateId": "integer"
      },
      "tuple_array_fields": {
        "asks": ["price_decimal_string", "quantity_decimal_string"],
        "bids": ["price_decimal_string", "quantity_decimal_string"]
      }
    },
    "payload_time_semantics": {
      "E": "server_output_time_ms",
      "T": "transaction_time_ms"
    }
  },
  "binance_usdm_rest_premium_index_v1": {
    "expected_response_schema": {
      "root_type": "object",
      "root_array": null,
      "required_fields": {
        "estimatedSettlePrice": "decimal_string",
        "indexPrice": "decimal_string",
        "interestRate": "decimal_string",
        "lastFundingRate": "decimal_string",
        "markPrice": "decimal_string",
        "nextFundingTime": "ms_timestamp",
        "symbol": "literal_BTCUSDT",
        "time": "ms_timestamp"
      },
      "tuple_array_fields": {}
    },
    "payload_time_semantics": {
      "nextFundingTime": "next_scheduled_funding_time_ms",
      "time": "payload_observation_time_ms"
    }
  },
  "binance_usdm_rest_funding_rate_v1": {
    "expected_response_schema": {
      "root_type": "array",
      "root_array": {"exact_length": 1, "item_type": "object"},
      "required_fields": {
        "fundingRate": "decimal_string",
        "fundingTime": "ms_timestamp",
        "markPrice": "decimal_string",
        "rateType": "enum_Regular_Special",
        "symbol": "literal_BTCUSDT"
      },
      "tuple_array_fields": {}
    },
    "payload_time_semantics": {
      "fundingTime": "realized_funding_event_time_ms"
    }
  },
  "binance_usdm_rest_open_interest_hist_5m_v1": {
    "expected_response_schema": {
      "root_type": "array",
      "root_array": {"exact_length": 1, "item_type": "object"},
      "required_fields": {
        "sumOpenInterest": "decimal_string",
        "sumOpenInterestValue": "decimal_string",
        "symbol": "literal_BTCUSDT",
        "timestamp": "ms_timestamp"
      },
      "tuple_array_fields": {}
    },
    "payload_time_semantics": {
      "timestamp": "period_end_time_5m_ms"
    }
  }
}
```

`canonical_json` sorts all object keys lexically, so the literal display order above is explanatory while the resulting serialized ProfileCore bytes and hash are unique. The top-level `extra_fields_policy="allowed"` remains the single authority for benign response extras; it is deliberately not duplicated inside `expected_response_schema`.

这四个 endpoint 的 public API 文档是 profile version 的外部参考，而 runtime hard cap 始终为 4，不能因 documented weight/rate-limit 而增加请求数。[Binance USD-M market-data documentation](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data)

## 4. Profile Attestation And Exact Identities

### 4.1 ProfileCore and attestation envelope

```text
profile_attestation_sha256 =
SHA256(UTF8(canonical_json(ProfileCore)))
```

`source_profile_attestations/<profile_id>.json` is a first-party envelope with exactly:

```text
schema_version = stage1_6e_a_profile_attestation_v1
capability_run_id
market_source_profile_id
profile_attestation_sha256
profile_attested_at_ms
permissions
```

The hash is not a ProfileCore key. Every network request requires the matching ProfileCore and its pre-request envelope to have been atomically written and read back successfully.

### 4.2 Capability run and request identities

```text
capability_run_id =
stage1_6e_a_capability_<UTC YYYYMMDDTHHMMSSZ>_<uuid4 lowercase hex>

regex = ^stage1_6e_a_capability_[0-9]{8}T[0-9]{6}Z_[0-9a-f]{32}$
```

The root must be fresh. A pre-existing root is a hard reject, so an ID collision is not silently reused.

```text
request_identity = SHA256(UTF8(canonical_json({
  "method": ProfileCore.method,
  "scheme": ProfileCore.scheme,
  "host": ProfileCore.host,
  "path": ProfileCore.path,
  "canonical_query": ProfileCore.canonical_query
})))
```

`probe_request_seq` is the canonical ProfileCore order in Section 3, starting at 1. It is immutable and each value is admitted at most once.

```text
market_capability_observation_id = SHA256(UTF8(canonical_json({
  "capability_run_id": capability_run_id,
  "market_source_profile_id": market_source_profile_id,
  "profile_attestation_sha256": profile_attestation_sha256,
  "probe_request_seq": probe_request_seq,
  "request_identity": request_identity,
  "outcome_kind": outcome_kind,
  "http_status": http_status_or_null,
  "raw_payload_persisted": raw_payload_persisted,
  "raw_sha256": raw_sha256_or_null,
  "observed_bytes_lower_bound": observed_bytes_lower_bound
})))
```

`canonical_json` means UTF-8 JSON, lexical key sorting and compact separators. No pipe-delimited or other ambiguous concatenation is permitted.

Every SHA-256 digest value emitted by E-A is exactly 64 lower-case ASCII hexadecimal characters: `^[0-9a-f]{64}$`. This applies to identity, attestation, raw, terminal and manifest digest fields; a digest with any other representation is invalid evidence.

## 5. Probe, Observation, And Failure Contract

All Stage 1.6E-A operational/resource/network thresholds are defined only in `configs/base.py`; `src/` and `scripts/` may import them but may not contain threshold literals. Required E-A SSOT names are:

```text
EXTERNAL_SIGNAL_STAGE1_6E_A_HTTP_TIMEOUT_SEC
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_PROFILES
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NETWORK_REQUESTS_PER_ROOT
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_MAX_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_ORDINARY_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_EMERGENCY_RESERVE_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NONTERMINAL_METADATA_DURABLE_BYTES
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_MANIFEST_DURABLE_BYTES
```

Existing `EXTERNAL_SIGNAL_STAGE1_5_*` host thresholds remain their sole shared-host SSOT; E-A must not duplicate them. Schema versions, profile IDs, endpoint paths and canonical queries are code-contract constants, not operational thresholds.

One profile is processed at a time in Section 3 order. The shared storage lock covers only one write admission and atomic replacement; it never covers DNS, TLS, network I/O or parsing. Every request uses `EXTERNAL_SIGNAL_STAGE1_6E_A_HTTP_TIMEOUT_SEC = 10.0`; the client applies it to socket connect/read. A timeout exception is `profile_timeout`, causes no retry and stops later network admission.

Every request has `Accept-Encoding: identity`, `redirect_policy=no_follow`, no authorization, no cookie, and no request body. `EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES` applies to exact HTTP entity-body bytes before JSON parsing and persistence. A non-identity `Content-Encoding` response is `profile_response_invalid`; the implementation must not transparently decode a body and then treat altered bytes as raw evidence.

`capability_observations.jsonl` contains one durable observation record for every request that reached a durable outcome. Its exact base key set is:

```text
schema_version = stage1_6e_a_capability_observation_v1
market_capability_observation_id
capability_run_id
market_source_profile_id
profile_attestation_sha256
probe_request_seq
request_identity
outcome_kind = response_persisted | response_not_persisted
local_observed_at_ms
http_status
response_headers_subset
raw_payload_persisted
raw_relative_path
raw_sha256
observed_bytes_lower_bound
payload_schema_status
payload_time_status
profile_status
terminal_classification
permissions
```

```text
payload_schema_status = verified | invalid | not_evaluable
payload_time_status = verified | invalid | not_evaluable
profile_status = capability_pass | capability_blocked | capability_failed
terminal_classification = continue | terminal_blocked | terminal_failed
```

`payload_time_status=verified` means only that the required payload time field is present and conforms to the frozen ProfileCore primitive grammar and declared mapping. It does not independently prove the exchange's real-world time semantics, PIT availability, or any trading conclusion.

`capability_not_probed` occurs only in the summary for a profile with no observation record. `response_headers_subset` has exactly lower-case `content-type`, `content-length`, `content-encoding`, `date`, and `retry-after`, each string or `null`. The `outcome_kind` value is included in the observation-ID projection in Section 4; `response_not_persisted` records cannot claim a complete payload hash or path.

### 5.1 Raw evidence union

| Outcome | `raw_payload_persisted` | `raw_relative_path` | `raw_sha256` | `observed_bytes_lower_bound` |
|---|---:|---|---|---:|
| Complete response was admitted, atomically persisted and read-back hashed | `true` | `raw/<raw_sha256>.body` | exact SHA-256 of complete stored bytes | exact byte count |
| Transport/HTTP/schema error with fully read body successfully persisted | `true` | `raw/<raw_sha256>.body` | exact SHA-256 of complete stored bytes | exact byte count |
| Timeout/no complete body, or storage admission/write failure before complete persistence | `false` | `null` | `null` | bytes read so far, or `0` |
| Body exceeded 2,000,000 bytes | `false` | `null` | `null` | `2_000_001` minimum; collector stops reading at limit plus one byte |

`raw_sha256` is never a partial-body hash presented as a full response hash. A raw-persist failure is local durability failure, never a valid profile pass.

For a complete root, the four persisted observations need not have four distinct payload hashes. Let `H = sorted(set(raw_sha256 from the four observations))`; the exact raw tree is `raw/<sha>.body` for every and only `sha in H`. Therefore `1 <= len(H) <= 4`, while the number of complete capability observations remains exactly four.

### 5.2 Two-layer profile and terminal reducer

Profile summary state is exactly one of:

```text
capability_pass
capability_blocked
capability_failed
capability_not_probed
```

`P1..P4` denotes the Section 3 profile order. The two layers below are mandatory and ordered. Layer A produces exactly one provisional response outcome. Layer B always runs after Layer A and owns all observation/terminal durability decisions. For every terminal result, later profiles are `capability_not_probed`; no later network request is admitted.

#### Layer A: response outcome reducer

Evaluate Layer A conditions in the listed order and apply only the first matching row. A lower Layer A row is not evaluated once a higher Layer A row wins. The result is not yet a durable observation and is only a provisional profile/terminal intent. `response_persisted` means that the complete bounded raw body was atomically persisted and read back; it does not mean `capability_observations.jsonl` is durable.

| Condition | Provisional `outcome_kind` / raw | schema / time | provisional profile / terminal intent |
|---|---|---|---|
| Socket timeout | `response_not_persisted`; `false` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_timeout` |
| Transport failure without HTTP response | `response_not_persisted`; `false` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_transport_blocked` |
| Body exceeds byte cap | `response_not_persisted`; `false` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_response_too_large` |
| Raw persistence/read-back/hash failure | `response_not_persisted`; `false` | `not_evaluable` / `not_evaluable` | `capability_failed` / `failed:storage_write_blocked` |
| Redirect response, no follow | `response_persisted`; `true` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_redirect_blocked` |
| HTTP non-2xx, non-redirect response | `response_persisted`; `true` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_http_blocked` |
| Non-identity `Content-Encoding` | `response_persisted`; `true` | `not_evaluable` / `not_evaluable` | `capability_blocked` / `blocked:profile_response_invalid` |
| Empty or non-JSON entity body | `response_persisted`; `true` | `invalid` / `not_evaluable` | `capability_blocked` / `blocked:profile_response_invalid` |
| JSON parses but frozen schema/token fails | `response_persisted`; `true` | `invalid` / `not_evaluable` | `capability_blocked` / `blocked:profile_schema_drift` |
| JSON schema verifies but payload time semantic fails | `response_persisted`; `true` | `verified` / `invalid` | `capability_blocked` / `blocked:profile_time_drift` |
| Valid P1, P2, or P3 response | `response_persisted`; `true` | `verified` / `verified` | `capability_pass` / `continue` |
| Valid P4 response | `response_persisted`; `true` | `verified` / `verified` | `capability_pass` / `complete:null`, conditional on all four Layer B observation records being durable |

Layer A terminal intent maps to the serialized observation field exactly as follows:

```text
continue          -> terminal_classification = continue
complete:null     -> terminal_classification = continue
blocked:<reason>  -> terminal_classification = terminal_blocked
failed:<reason>   -> terminal_classification = terminal_failed
```

`complete:null` is a Layer-B-only terminal intent. It is never serialized as `observation.terminal_classification`; only a durable `terminal_status.json` may assert `status=complete`.

#### Layer B: durability finalization reducer

Layer B runs exactly once after every Layer A outcome:

1. Construct the complete observation from the Layer A outcome using the exact terminal-intent mapping above, then atomically persist/read back `capability_observations.jsonl`.
2. If observation persistence/read-back fails, no durable observation ID exists; it supersedes the Layer A outcome. Mark the current profile `capability_failed`, construct terminal intent `failed:local_integrity_failed`, and stop later network admission.
3. Otherwise, retain the Layer A profile/terminal intent. `continue` admits only the next fixed profile. A blocked or failed Layer A intent constructs that terminal. A P4 `complete:null` intent constructs a complete terminal only when all four observation records are durable.
4. For every constructed terminal intent, atomically persist/read back `terminal_status.json`. If that fails, it supersedes the prior terminal intent: no valid terminal exists, no manifest is written, the process exits non-zero, and the root is unsealed/nonconsumable.

For any `response_persisted` Layer A row, the complete bounded entity body is atomically stored and read back before parsing. For any `response_not_persisted` row, `raw_relative_path` and `raw_sha256` are `null`. It is not resumable; any retry uses a fresh root.

## 6. Storage, Execution Environment, And Lifecycle

E-A production root is a direct fresh child only:

```text
data/external_signal_shadow/stage1_6e/capability_audits/<capability_run_id>
```

It runs only on the Section 1 VPS. The deployment preflight must prove the root resolves on the same filesystem and the derived lock equals:

```text
data/external_signal_shadow/.stage1_5_storage_guard.lock
```

The implementation must copy the narrow stdlib lock derivation and storage-reservation semantics used by Stage 1.6B. It must not import `stage1_5_storage_guard.py`, Stage 1.5 runtime code, 1.6D writer code, strategy, execution, account or order modules.

The fresh root is protected for the process lifetime by `.stage1_6e_a_writer.lock`; it is an allowed zero-byte-or-small regular file and must remain unchanged after acquisition. It is not semantic evidence, but a complete manifest includes it so the closed-tree rule has no implicit exception.

```text
host_start_free_bytes = 8 GiB
host_protected_reserve_bytes = 4 GiB
host_ordinary_control_plane_reserve_bytes = 52 MiB
host_emergency_blocker_reserve_bytes = 12 MiB

root_max_bytes = 16 MiB
root_ordinary_control_plane_reserve_bytes = 1 MiB
root_emergency_blocker_reserve_bytes = 256 KiB
terminal_write_set_max_peak_bytes = 64 KiB

max_raw_durable_bytes = 4 * 2_000_000 = 8_000_000
max_nonterminal_metadata_durable_bytes = 512 KiB
max_manifest_durable_bytes = 128 KiB
```

The required `configs/base.py` values are exactly:

```text
EXTERNAL_SIGNAL_STAGE1_6E_A_HTTP_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES = 2_000_000
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_PROFILES = 4
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NETWORK_REQUESTS_PER_ROOT = 4
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_MAX_BYTES = 16 MiB
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_ORDINARY_RESERVE_BYTES = 1 MiB
EXTERNAL_SIGNAL_STAGE1_6E_A_ROOT_EMERGENCY_RESERVE_BYTES = 256 KiB
EXTERNAL_SIGNAL_STAGE1_6E_A_TERMINAL_WRITE_SET_MAX_PEAK_BYTES = 64 KiB
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_NONTERMINAL_METADATA_DURABLE_BYTES = 512 KiB
EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_MANIFEST_DURABLE_BYTES = 128 KiB
```

Normal data/manifest writes reserve the existing host protected + ordinary + emergency reserves and the root ordinary + emergency reserves. Terminal writes reserve the protected host reserve, root maximum, and `terminal_write_set_max_peak_bytes`; no admission deletes or weakens another root's reserve.

The shared host emergency invariant is mandatory and must be a config/test assertion:

```text
12 MiB
>= Stage 1.5D terminal peak (2 MiB)
 + Stage 1.5F terminal peak (2 MiB)
 + Stage 1.6D/1.6B terminal peak (256 KiB)
 + Stage 1.6E-A terminal peak (64 KiB)
= 4_521_984 bytes
```

`root_max_bytes - root_ordinary_control_plane_reserve_bytes - root_emergency_blocker_reserve_bytes = 15_466_496 bytes`, which exceeds `8_000_000 + 512 KiB + 128 KiB`. Each write reconciles only this root before admission; no periodic root-wide scan, auto-delete, root reuse or crash resume exists.

State machine:

```text
new -> probing -> terminal_complete | terminal_blocked | terminal_failed
```

Only `terminal_complete` is eligible for sealing. `terminal_blocked`, `terminal_failed`, missing terminal, or manifest-write failure are preserved but nonconsumable. E-A has no resume path.

## 7. Terminal, Closed Bundle, And Summary

`terminal_status.json` has exactly:

```text
schema_version = stage1_6e_a_terminal_status_v1
capability_run_id
status = complete | blocked | failed
terminal_reason
started_at_ms
terminal_at_ms
profile_attestation_sha256_by_id
attempted_profile_ids
passed_profile_ids
accounted_root_bytes
permissions
```

`attempted_profile_ids` is the strict Section 3 order prefix for which one network request was admitted. `passed_profile_ids` is its strict-order subset whose profile state is `capability_pass`. A complete terminal has both lists equal to all four profile IDs; a blocked/failed terminal never lists an unprobed profile as attempted or passed.

`terminal_reason` is `null` only for `status=complete`. For `status=blocked`, it is exactly one of `profile_timeout`, `profile_transport_blocked`, `profile_redirect_blocked`, `profile_http_blocked`, `profile_response_invalid`, `profile_schema_drift`, `profile_time_drift`, or `profile_response_too_large`. For `status=failed`, it is exactly `storage_write_blocked` or `local_integrity_failed`.

`capability_summary.json` includes one Section 5.2 profile state per fixed profile, its observation ID or `null`, and these fixed non-conclusions:

```text
historical_retention_coverage = not_evaluable
event_market_coverage = not_evaluable
fee_coverage_status = not_evaluated_in_stage1_6e_a
```

`manifest.json` is permitted only after a valid `terminal_status.status=complete`. It has exactly:

```text
schema_version = stage1_6e_a_manifest_v1
manifest_id
capability_run_id
terminal_status_sha256
profile_attestation_sha256_by_id
authoritative_artifacts
permissions
```

`manifest_id = SHA256(UTF8(canonical_json(manifest with only manifest_id omitted)))`.

For a complete root, `authoritative_artifacts` sorted strictly by `relative_path` must equal every allowed durable regular file in the root other than `manifest.json` itself:

```text
execution_environment_attestation.json
source_profiles/<each of the four profile IDs>.json
source_profile_attestations/<each of the four profile IDs>.json
.stage1_6e_a_writer.lock
capability_observations.jsonl       # exactly four records
raw/<raw_sha256>.body               # exactly one per SHA in H; 1..4 files
capability_summary.json
terminal_status.json
```

Each entry is `{relative_path, sha256, byte_count}`. A complete root rejects any symlink, temporary/orphan file, nested unknown path, unmanifested regular file, missing required file, duplicate path, out-of-order list, incorrect byte count/hash, or artifact not permitted by the exact tree above. `manifest.json` is excluded from its own list to avoid a hash cycle. A complete terminal without a valid closed-tree manifest is unsealed, nonconsumable evidence and does not authorize E-B.

## 8. Acceptance Invariants And Verification

| ID | Invariant |
|---|---|
| INV-EA-01 | Production capability evidence is generated only on the approved VPS/filesystem/network-namespace/proxy-policy environment; local results are test-only. |
| INV-EA-02 | ProfileCore hashes exclude the attestation envelope and bind a pre-request, immutable profile. |
| INV-EA-03 | `capability_run_id` follows the exact frozen timestamp/UUID grammar; `request_identity` and `market_capability_observation_id` use only the exact canonical UTF-8 JSON SHA-256 formulas in Section 4. |
| INV-EA-04 | Every profile validates its frozen root/type/required-field/extra-field/time semantics; no inferred event time exists. |
| INV-EA-05 | A response has exact raw evidence or explicit raw-not-persisted evidence; no partial content hash is promoted. |
| INV-EA-06 | Four sequential, single-attempt probes have unambiguous pass/blocked/failed/not-probed and terminal reduction. |
| INV-EA-07 | Every persistent write is admitted under the shared lock and the verified host/root reserve algebra; no Stage 1.5 runtime import exists. |
| INV-EA-08 | A sealed complete root has an exact closed artifact tree and manifest; any other root is nonconsumable. |
| INV-EA-09 | E-A does not consume 1.6D evidence and grants no event/PIT/coverage/replay/alpha/execution/trading authority. |

The future Plan must include at least:

1. golden ProfileCore, UTF-8 canonical bytes and all identity digests;
2. four profile success fixtures plus root/type/field/tuple/enum/time drift rejects;
3. timeout, redirect, 418/429, oversized body and raw-persist failure reducers;
4. profile `not_probed` and local `failed` state cases, plus P4 success (`terminal_classification=continue`, durable complete terminal) and P4 terminal-write failure (`terminal_classification=continue`, no valid terminal or manifest);
5. lock serialization, normal/terminal admission boundaries and the four-runtime emergency-reserve equation;
6. environment-attestation identity checks; manifest complete-tree acceptance including repeated raw SHA, and each missing/unknown/symlink/tmp/hash/byte-count rejection;
7. static import/AST checks for no Stage 1.5 runtime, strategy, execution, account/order or 1.6D root consumer;
8. VPS-only production preflight proving the exact environment-attestation fields, fresh root, 8 GiB start space and unchanged false permissions.

## 9. Approval Layers

```text
Design approval
  -> permits Implementation Plan writing only

Implementation Plan approval + explicit user authorization
  -> permits code implementation only

implemented code + passing review + separate explicit VPS runtime/deployment authorization
  -> permits one real VPS capability probe
```

No Plan approval, implementation approval or local test result authorizes a real VPS network request. This Design is not a VPS deployment authorization.

## 10. Explicit Deferral To E-B

E-A must not implement or authorize:

```text
live semantic adapter/reducer
active 1.6D checkpoint transport
system_available_at_ms or fact_available_at_ms stamping
revision supersession lifecycle
event-symbol trigger/deduplication
event coverage profile, slots or denominator
event-market observation/retry/duplicate semantics
per-event L2, price, funding, OI or fee collection
event-root checkpoint, terminal or sealed-export contract
market_data_coverage_audit_passed
PIT, replay, alpha, execution, paper or live trading
```

E-B requires its own approved Design, governance, producer/consumer contract, VPS deployment authorization and storage/terminal/manifest review. A sealed E-A result is candidate profile evidence only, not E-B permission.
