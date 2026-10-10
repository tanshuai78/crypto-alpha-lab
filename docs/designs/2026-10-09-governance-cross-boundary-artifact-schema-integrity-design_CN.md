# Governance Cross-Boundary Artifact Schema Integrity Design

**日期:** 2026-10-09
**状态:** `revision_for_closure_confirmation`
**目的:** 在项目级阻断跨信任边界持久化产物的 producer-loader co-drift；首个冻结 profile 以 J-A parent Design 的完整 structural contract 定义独立验证边界，不把 verifier 自身变成可漂移权威。
**本 Design 不授权:** implementation、commit、push、network、receipt generation、deployment、SSH、replay、signal、paper trading、live trading、execution 或 J-B upstream consumption。

---

## 1. Confirmed Facts

1. Stage 1.5J-A 曾出现 producer 写入与 strict loader 接受同一未批准 journal grammar 的 co-drift。共同实现可以同时遗漏字段、接受非法 enum 或放宽 conditional context，因而不能单独构成 closure evidence。
2. 当前 workspace 存在真实 J-A receipt。以下是已从 workspace bytes 重算的 immutable `known_nonconforming_reference` identity；它是 profile 的真实负例，不是本 Design 可修改的 fixture、positive conformance evidence 或 downstream admission：

```text
RUN_ID = stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z
ROOT_RELATIVE_PATH = data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/
                     stage1_5j_a_historical_archive_coverage_inventory_20261008T160500Z
manifest.json          = afce37097f9d7ab0732afe0164cbc918f2d263788fd4b41be674536ba1cee21c
summary.json           = 2cf233c476b4ad43ea8105a274af38cc1fd595e1b22012966ceb656aa68aa7a7
review_CN.md           = 38917ed3014b4e6b758cc3900f67925c4cb942cc73b879c0fa90da0135b219b5
request_journal.jsonl  = 139453f07072d3f31ad3d398434a12bc7786cda30003bdd0cf7e8f3d23ed5582
```

3. 该 root 当前有 709 个 regular files、无 discovered symlink；`manifest.json` 与 `summary.json` 均为 UTF-8 canonical JSON。其 schema versions 分别为 `stage1_5j_a_historical_archive_coverage_inventory_manifest_v1` 与 `stage1_5j_a_historical_archive_coverage_inventory_v1`，run ID 与 root-relative path 一致。
4. 该 root 的 `AIAUSDT` record 为 `child_state=archive_request_nonpersisted`，却写入 `post_launch_row_count=0`。父级 J-A Design 对该 state 明确要求四个 trade fields 全为 `null`，其中包括 `post_launch_row_count`。因此它是已证实的 J-A conformance defect 证据；后续 verifier 必须以 `rc=1` 拒绝它，不能为了历史兼容而放宽 profile。
5. J-A parent Design 已冻结 sealed tree、canonical JSON、完整 nested summary schema、journal state machine 与 receipt closure timing。Governance verifier 必须复制其 structural obligation，不能只检查 summary 外壳；coverage formula、parser projection、authority disk provenance 和 Markdown rendering 仍属 J-A domain loader/closure audit。
6. 当前 repository 没有 independent governance schema verifier。`graphify-out/graph.json` 存在，但 `.venv` 未安装 `graphify`；本 Design 的影响结论来自 parent Design、current source、receipt bytes、existing audit skill 与 `rg`，不是 graph query。

## 2. Scope And Non-Goals

### 2.1 In scope

1. 在 `.agent/rules/L1_Engineering_Process.md` 增加 Rule 17，并在 `AGENTS.md` 同步项目级摘要。
2. 新增一个只读、stdlib-only CLI：`scripts/governance/verify_artifact_schema.py`。首版只支持一个内置、immutable profile：`stage1_5j_a_receipt_v1`。
3. 新增该 CLI 的测试；更新 Plan review、Completion/Closure Audit skill checklist 与 tri-agent Prompt library。
4. 将 profile authority tuple、sealed-root identity、nested structural schema、independent verifier identity 和 receipt/downstream evidence 绑定成项目级可复用治理规则。

### 2.2 Explicit non-goals

1. 不创建 profile registry、plugin/factory、YAML/JSON runtime schema language、`--schema-spec`、`--design-path` parser、用户自定义 profile 或自动发现 artifact type。
2. 不将 Markdown 当作 JSON schema。`review_CN.md` 仅验证 sealed-tree membership、byte count 和 SHA-256；其 renderer projection 继续由所属 stage 的 loader/closure audit 验证。
3. 不替换、导入、调用或包装任一 target stage producer、loader、CLI 或 test；不修改 J-A/J-B source、receipt、fixture、network authorization 或 data root。
4. 不把 verifier pass 解释为 semantic reduction、数据经济价值、Alpha、PIT、可执行性、J-B rebind 或任意交易权限。
5. 不修改 `configs/base.py`、风险阈值、执行模块、VPS、project-status、roadmap 或现有 J-B draft。

## 3. Trust Boundary And Profile Authority

### 3.1 Frozen TCB

本 Design 的 TCB 仅为：approved Governance Design exact bytes、后续 completion-audited verifier exact bytes、CPython/stdlib、OS `lstat`/regular-file semantics 与 SHA-256。J-A producer、J-A loader、target tests、CLI `--artifact-root` 输入、artifact bytes、任意 stage runtime output 都不可信，必须被独立检查。该定义不尝试下探 Python/OS/supply-chain 威胁模型。

### 3.2 Rule 17: Cross-Boundary Artifact Schema Integrity

后续实施必须在 L1 增加以下规则，并在 `AGENTS.md` 简述同一要求：

```text
17. Cross-Boundary Artifact Schema Integrity:
For every newly created or revised persistent artifact that crosses a producer/
consumer, process, lifecycle, or downstream-stage trust boundary, its approved
Design/Plan MUST name an immutable profile authority tuple, exact key sets,
legal enum literals, conditional field combinations, sealed-tree/path rules,
and deterministic byte/projection obligations. A producer and its domain loader
MUST each enforce their contract. Completion and receipt-closure audits MUST
additionally run an independently implemented artifact verifier whose acceptance
logic derives only from its literal approved profile constants and artifact bytes,
not from the target producer or loader. The audit record MUST bind the exact
approved Design SHA, verifier source SHA, profile ID/version and receipt identity.
Internal pure-logic unit tests remain exempt when they prove no cross-boundary
artifact claim.
```

Rule 17 applies only to persistent artifacts that cross a trust boundary. It does not require an exact-key schema for every local dict, debug log or human-authored Markdown note. Each approved Design must declare whether a field is protected by an exact structured schema, deterministic renderer projection, or sealed manifest byte/hash binding.

### 3.3 Immutable profile authority tuple

Every profile, including v1, has an external evidence tuple:

```text
profile_id
profile_contract_version
governance_design_relative_path
governance_design_sha256
target_stage_design_relative_path + sha256
target_stage_delta_relative_path + sha256, if applicable
verifier_relative_path + verifier_source_sha256
receipt_root_relative_path
manifest_sha256 + summary_sha256 + review_sha256 + request_journal_sha256
```

For `stage1_5j_a_receipt_v1`, the target identities are:

```text
target_stage_design = docs/designs/2026-10-05-external-signal-shadow-lab-stage1-5j-a-historical-archive-coverage-inventory-design_CN.md
target_stage_design_sha256 = b74c306e92b2bd72935b6791ac5ee38889d27887c90be31c55457a223e4fc15a
target_stage_delta = docs/designs/2026-10-08-external-signal-shadow-lab-stage1-5j-a-conformance-remediation-design-delta_CN.md
target_stage_delta_sha256 = 6063ed103d31fcf6c60ad8106eb13650f54b74272182c78bf8e81f9ba48a91ac
profile_id = stage1_5j_a_receipt_v1
profile_contract_version = 1
```

The governance Design SHA and verifier source SHA are deliberately recorded by the approved Plan, Completion/Closure Audit or downstream admission evidence, not self-asserted by the verifier. A script cannot establish trust in its own bytes by comparing against a hash stored in those same mutable bytes. Any acceptance-semantics change requires a new `profile_id` and `profile_contract_version`; retaining the identifier while loosening or extending its accepted grammar is forbidden.

## 4. One Frozen Profile, Not A Framework

The later implementation supports only this profile and project-relative root argument shape:

```bash
python3 scripts/governance/verify_artifact_schema.py \
  --profile stage1_5j_a_receipt_v1 \
  --artifact-root <project-relative-j-a-v1-root>
```

The Section 1 root is a required negative real-root invocation: it must return `rc=1` and identify `archive_request_nonpersisted.post_launch_row_count` as expected `null`, observed `0`. It is not an example of CLI success.

`--artifact-root` is a required project-relative POSIX path: absolute paths, empty components, `.` and `..` are rejected. The script derives the project root from its own fixed repository location; it accepts no project-root override. From that project root through every lexical component of the artifact root, and through every traversed descendant, `lstat` must report non-symlink regular files/directories as appropriate. The normalized argument must equal manifest `root_relative_path`, which must exactly equal:

```text
data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/<manifest.run_id>
```

The script imports only Python standard-library modules. Acceptance logic may use only literal profile constants and bytes beneath the validated artifact root. It must not import, execute, inspect or read target producer/loader/CLI/test source; invoke a subprocess; use `importlib`, `runpy`, `exec`, `eval`, `compile` or dynamic `__import__`; inspect `.git`; call a network API; or write project files. A future artifact family requires a separately approved Design and Plan, not configuration or a generic runtime parser.

## 5. `stage1_5j_a_receipt_v1` Structural Contract

### 5.1 Sealed-root identity and manifest

The verifier requires these literal schema versions and run ID grammar:

```python
SUMMARY_SCHEMA_VERSION = "stage1_5j_a_historical_archive_coverage_inventory_v1"
MANIFEST_SCHEMA_VERSION = "stage1_5j_a_historical_archive_coverage_inventory_manifest_v1"
RUN_ID_REGEX = r"stage1_5j_a_historical_archive_coverage_inventory_[0-9]{8}T[0-9]{6}Z"
SHA256_REGEX = r"[0-9a-f]{64}"
```

`manifest.run_id == summary.run_id == artifact_root.name`; both schema versions must equal the literals above. `manifest.json` and `summary.json` must be UTF-8 without BOM, sorted object keys, `,`/`:` separators and exactly one terminal newline. Their parsed/re-encoded canonical bytes must equal disk bytes.

```python
MANIFEST_EXACT_KEYS = frozenset({
    "artifacts", "root_relative_path", "run_id", "schema_version",
})
MANIFEST_ARTIFACT_EXACT_KEYS = frozenset({
    "byte_count", "relative_path", "sha256",
})
```

`artifacts` is a lexicographically ordered, duplicate-free list of safe relative paths. It lists every regular final-root file except `manifest.json`; it never lists itself. Each entry has exact keys, a non-bool nonnegative integer `byte_count` and lowercase SHA-256 grammar. The observed final root must contain exactly `manifest.json` plus those listed files, and only directories implied by those paths. Any extra file, directory, path alias, unlisted file, symlink or missing listed file is a STOP.

Allowed file paths are exactly `summary.json`, `review_CN.md`, `request_journal.jsonl`, `raw/catalog_scan_a/<positive-page>.json`, `raw/catalog_scan_b/<positive-page>.json`, `raw/article_details/<32-lower-hex>.json`, `raw/archive/<UPPERCASE-USDT-symbol>/<same-symbol>-aggTrades-<YYYY-MM-DD>.zip`, and the adjacent `.zip.CHECKSUM`. The verifier checks all listed file byte counts and SHA-256 values and requires `summary.json`, `review_CN.md`, and `request_journal.jsonl` as manifest members.

### 5.2 Summary exact schema

```python
SUMMARY_EXACT_KEYS = frozenset({
    "analysis_state", "archive_package_records", "authority_flags",
    "authority_packet", "catalog_denominator_records", "catalog_scan",
    "coverage_inventory", "decision", "parent_records", "request_records",
    "run_id", "schema_version", "universe_window",
})
AUTHORITY_FLAG_EXACT_KEYS = frozenset({
    "alpha_claim_allowed", "alpha_interpretation_allowed", "commit_allowed",
    "deployment_allowed", "execution_allowed", "live_trading_allowed",
    "network_allowed_after_run", "paper_trading_allowed",
    "pnl_calculation_allowed", "price_response_calculation_allowed",
    "receipt_generation_allowed_without_authorization", "replay_allowed",
    "signal_generation_allowed",
})
```

All 13 authority values must be literal JSON `false`. The verifier checks the following nested exact-key/type/enum/nullable contract independently, but does not recompute any reducer formula or parser-derived mapping:

| object | exact structural rule |
| --- | --- |
| `universe_window` | exact `end_exclusive_ms,start_ms`; both non-bool integers |
| `catalog_scan` | exact `page_limit_per_pass,scan_a_page_count,scan_b_page_count,sentinel_page_no,stable_tuple_sha256`; counts/page values positive non-bool integers; digest matches SHA grammar |
| `authority_packet` | exact `approved_design,approved_plan,audited_cli,audited_config,audited_core,frozen_parser,network_authorization`; first six have exact `relative_path,sha256`; network authorization additionally has exact `authorized_run_id,network_profile_id`; paths are safe project-relative strings and all SHA fields use SHA grammar |
| `catalog_denominator_records[]` | exact `candidate_status,detail_request_id,release_date_ms,source_article_id,title`; list equals its stable sort by `(release_date_ms, source_article_id)`; status is `not_target_event_type`, `catalog_detail_unresolved` or `resolved_target_parent`; source ID is 32-lower-hex; title is string; release date is non-bool integer; detail ID is null iff status is `not_target_event_type`, otherwise positive non-bool integer |
| `parent_records[]` | exact `children,detail_payload_sha256,detail_request_id,detail_status,parent_state,source_article_id`; list equals its stable sort by `source_article_id`; source ID is 32-lower-hex; detail status is `validated_target_detail`, `detail_nonpersisted`, `detail_title_disagreement` or `detail_parser_unresolved`; parent state is `coverage_complete`, `coverage_evidence_gap_detail`, `coverage_evidence_gap_no_in_scope_usdt_child` or `coverage_evidence_gap_archive` |
| parent conditional fields | every parent has a positive detail request ID; only `validated_target_detail` has a SHA digest and children; `detail_nonpersisted` has null SHA; `detail_title_disagreement`/`detail_parser_unresolved` have SHA digest; every nonvalidated state has empty children and parent state `coverage_evidence_gap_detail` |
| `children[]` | exact `child_scope,symbol,symbol_launch_time_ms`; scope is `in_scope_usdt` or `out_of_scope_non_usdt`; symbol is nonempty uppercase string; launch time is non-bool integer |
| `archive_package_records[]` | exact `checksum_request_id,child_state,first_post_launch_trade_delay_ms,first_post_launch_trade_time_ms,last_post_launch_trade_time_ms,logical_archive_identity,parent_article_id,post_launch_row_count,symbol,utc_date,zip_request_id`; list equals its stable sort by `(parent_article_id, symbol, utc_date)`; child state is `archive_verified_with_post_launch_rows`, `archive_verified_zero_post_launch_rows` or `archive_request_nonpersisted` |
| archive conditional fields | `archive_verified_with_post_launch_rows` has positive non-bool request IDs/row count and non-null non-bool timestamp/delay fields; `archive_verified_zero_post_launch_rows` has positive IDs, row count zero and null time/delay fields; `archive_request_nonpersisted` has `post_launch_row_count`, `first_post_launch_trade_delay_ms`, `first_post_launch_trade_time_ms` and `last_post_launch_trade_time_ms` all null. The verifier does not add a request-ID combination rule beyond the parent Design. |
| `logical_archive_identity` | exact `market,metric,parent_article_id,symbol,utc_date`; literals `futures_um`/`aggTrades`; identity values equal their containing archive record; parent ID is 32-lower-hex; symbol/date satisfy the declared grammar |
| `request_records[]` | exact `http_status_or_transport_error,request_id,request_kind,request_state,response_bytes,response_relative_path,response_sha256,url`; this list must equal the deterministic completed-journal projection in §5.4, so its request-ID sequence is exactly the journal request-ID sequence; a persisted response path is safe, points to a manifest member and its SHA equals that member's SHA |
| `coverage_inventory` | exact `catalog_denominator_count,child_coverage_complete_count,child_coverage_gap_count,in_scope_usdt_child_count,out_of_scope_child_count,parent_coverage_complete_count,parent_coverage_gap_count,resolved_parent_count,target_parent_count`; every value is a non-bool nonnegative integer |
| state/decision pair | only `coverage_inventory_complete` with `stage1_5j_a_historical_archive_coverage_inventory_published`, or `coverage_inventory_evidence_gap` with `stage1_5j_a_historical_archive_coverage_evidence_gap_published` |

### 5.3 Journal exact schema and state machine

The verifier processes JSONL line-by-line and requires:

```python
INTENT_EXACT_KEYS = frozenset({
    "event", "parent_article_id", "request_id", "request_kind",
    "request_state", "symbol", "url", "utc_date",
})
TERMINAL_EXACT_KEYS = frozenset({
    "event", "http_status", "request_id", "request_state",
    "response_bytes", "response_relative_path", "response_sha256",
    "transport_error",
})
REQUEST_KINDS = frozenset({"catalog", "detail", "archive", "checksum"})
TERMINAL_STATES = frozenset({
    "response_persisted", "http_not_found", "transport_inconclusive",
    "response_rejected",
})
```

Intent has `event="request_intent"`, `request_state="admitted_pending"` and a positive contiguous integer request ID. Context applicability is exact: `catalog` has all three context fields null; `detail` has only nonempty-string `parent_article_id`; `archive` and `checksum` have nonempty-string `parent_article_id`, `symbol` and `utc_date`.

Each ID has exactly one intent and exactly one terminal. A terminal must occur after its own intent; adjacency is not required. Terminal has `event="request_terminal"` and only these combinations:

| state | required fields |
| --- | --- |
| `response_persisted` | `http_status=200`, `transport_error=null`, all `response_*` non-null, `response_bytes` positive non-bool integer, safe response path and SHA grammar |
| `http_not_found` | `http_status=404`, `transport_error=null`, all `response_*` null |
| `transport_inconclusive` | `http_status=null`, nonempty-string `transport_error`, all `response_*` null |
| `response_rejected` | `http_status` non-bool integer other than 200/404, `transport_error=null`, all `response_*` null |

`http_non_200`, unknown keys, `created_at_utc`, duplicate terminal, dangling intent, missing context and incoherent terminal fields are all structural STOPs.

### 5.4 Completed-journal projection

For the journal's request IDs in ascending order, the verifier independently constructs one projection row from the matching intent and terminal:

```text
request_id                    = intent.request_id
request_kind                  = intent.request_kind
url                           = intent.url
request_state                 = terminal.request_state
http_status_or_transport_error = terminal.http_status for non-transport states,
                                 otherwise terminal.transport_error
response_bytes                = terminal.response_bytes
response_relative_path        = terminal.response_relative_path
response_sha256               = terminal.response_sha256
```

`summary.request_records` must byte-for-value equal that complete ordered projection. A valid journal and a separately valid-looking summary projection are insufficient: a mismatched URL, kind, terminal state, status/error, response path, SHA or byte count for any same request ID is a structural STOP. This check does not recompute catalog selection, parser projection, package validation or coverage formulas.

## 6. Acceptance Invariants

| ID | Invariant |
| --- | --- |
| INV-GSI-01 | Verifier acceptance logic derives only from literal profile constants plus validated artifact-root bytes; it cannot import, execute, inspect or derive acceptance from target code. |
| INV-GSI-02 | Every profile has an externally recorded authority tuple, and any acceptance-semantics change requires a new profile ID/version; profile name alone is never sufficient downstream evidence. |
| INV-GSI-03 | `stage1_5j_a_receipt_v1` independently enforces the complete parent-Design structural summary, journal and sealed-tree contract, including nested keys, primitive grammar, enum, nullable combinations, declared array orders and exact completed-journal projection. |
| INV-GSI-04 | Profile verification rejects noncanonical JSON, path substitution, symlink traversal, extra/missing files, manifest ordering/alias errors and root/run/schema identity mismatch. |
| INV-GSI-05 | Markdown is validated only by sealed-tree membership and hash; rendering semantics remain a separate J-A domain-loader obligation. |
| INV-GSI-06 | A profile pass is additional structural evidence only and cannot override a failed stage strict loader, authority verifier or receipt closure audit. |
| INV-GSI-07 | Plan review, Completion/Closure Audit and downstream admission require named profile identity, verifier SHA and real-root evidence whenever the approved Design declares that trust boundary. |
| INV-GSI-08 | No governance change enables network, receipt generation, replay, signal, paper/live trading, execution, Alpha claim or J-B consumption. |

## 7. Failure Semantics And Reference Provenance

The CLI is read-only and deterministic:

```text
rc=0  all declared profile checks pass
rc=1  profile contract violation; print profile, artifact, line/request ID where applicable,
      expected constraint and observed value
rc=2  invalid CLI use, unsupported profile, unreadable project-relative path or unsafe ancestry
```

It does not repair, normalize, skip, downgrade, fabricate defaults or continue after the first violation. It creates no output directory, receipt, sidecar, cache, lock or journal. Crash/recovery, staging, flock, fsync and rename remain producer lifecycle obligations; their resulting final tree is independently checked by this verifier.

The Section 1 root is immutable negative evidence. Its verifier record must recompute and record the four frozen hashes, exact approved Governance Design SHA, verifier source SHA, profile ID/version, `rc=1`, and the `post_launch_row_count expected null, observed 0` diagnostic. It cannot be recorded as positive structural evidence. A future J-A root may become positive evidence only after it has its own relative path and manifest/summary/review/journal hashes, the J-A strict loader succeeds, and the independent verifier returns `rc=0`; it may not borrow the Section 1 reference identity.

## 8. Verification Strategy And Governance Routing

### 8.1 Implementation tests

The later Plan must create `tests/scripts/governance/test_verify_artifact_schema.py` and require:

1. A smallest valid local tree for internal pure tool logic and CLI success. It proves verifier mechanics only, never cross-boundary positive evidence.
2. One-mutation negatives for every contract class: profile/version rejection; manifest schema/run/root mismatch; noncanonical JSON; path traversal, duplicate or unsorted manifest entry; missing/extra file or directory; root/ancestor/descendant symlink; manifest hash/byte mismatch; nested summary extra/missing key; invalid enum/primitive/nullable combination, including `archive_request_nonpersisted.post_launch_row_count: null -> 0`; non-false authority flag; each required summary-array ordering fault; and each request-records-to-journal projection field mismatch.
3. AST/static tests that permit only stdlib imports and reject target-module import/source loading, `importlib`, `runpy`, `subprocess`, `os.system`, dynamic `__import__`, `exec`, `eval`, `compile`, and calls outside the validated root traversal. The test also verifies the profile constants carry the frozen target stage identities.
4. A no-write assertion over the input tree and unknown-profile/absolute-path/parent-traversal CLI failures. The immutable Section 1 real root is invoked without mutation and must return the specified `rc=1` diagnostic.

### 8.2 Authoritative audit paths

Design/Plan Closure Audit and Closure Confirmation are governed by the `B-Design-Closure` route in `docs/production_artifacts/tri_agent_prompt_library_CN.md` plus the current project-designated Closure Audit skill named by that route. The route must resolve that skill to exact accessible bytes before review; otherwise it returns `EVIDENCE_GAP` rather than silently substituting a different methodology. The current workspace does not contain an on-disk `closure-audit-skill-v3.md`, so this Design neither invents a repository path nor claims to edit it.

Implementation Completion Audit and Completion Closure are governed by `.agent/skills/audit-plan-completion/SKILL.md`, invoked by the `A-Completion-Audit` and `A-Completion-Closure` routes. The governance implementation updates this existing skill and the relevant prompts, preserving the two routes rather than merging them into a new audit skill.

At an approved receipt closure or downstream admission, auditors run the independent verifier against the actual sealed root, independently record the authority tuple, then use only an isolated temporary copy for one declared mutation per probe. The verifier rejection and the stage strict loader's separate domain result are both required. A verifier-only pass does not grant semantic closure or consumer authority.

## 9. Allowed Future Implementation Surface

A subsequent approved Implementation Plan may whitelist only:

```text
AGENTS.md
.agent/rules/L1_Engineering_Process.md
.agent/skills/reviewing-implementation-plans/SKILL.md
.agent/skills/audit-plan-completion/SKILL.md
docs/production_artifacts/tri_agent_prompt_library_CN.md
scripts/governance/verify_artifact_schema.py
tests/scripts/governance/test_verify_artifact_schema.py
```

No J-A/J-B source, receipt, fixture, config, `data/` artifact, network authorization or project-status document is an implementation path. If implementation requires a target-stage contract change rather than an independent validator, it is `BLOCKED_SPEC_DRIFT` and requires a separate stage Design/Plan.

## 10. Authority And Routing

1. This revised Design requires Closure Confirmation and explicit user Design approval. It deliberately does not yet authorize drafting or implementing a governance verifier Plan.
2. Before that Plan, a separate narrow J-A conformance-remediation Design/Plan must repair the parent-contract defect, complete its pre-network audit, and leave the Section 1 root immutable and rejected by the repaired J-A loader.
3. After that pre-network J-A closure, an approved governance Plan plus user implementation authorization can permit only the listed governance code/document/test edits. It cannot authorize a network run, receipt generation, J-A/J-B modification or data-root write.
4. The future verifier becomes mandatory only where an approved stage Design/Plan names its profile and authority tuple. It does not retroactively recertify legacy roots.
5. A later single-use J-A network authorization may produce a new root. Only after both its J-A strict loader and the independent verifier pass may it become positive real-root evidence; J-B replacement-receipt rebind remains a separate Design Delta after that identity/projection/cardinality freeze.

There are no implementation-path open questions. This is deterministic governance infrastructure; all Alpha/economic/PIT/execution claims are `N/A`.
