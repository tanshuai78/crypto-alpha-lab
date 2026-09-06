# Stage 1.6E-B Completion Remediation Delta Design

- 日期: 2026-09-04
- 状态: `design_draft`
- Parent Design SHA-256: `752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583`
- Parent Plan SHA-256: `279f729645c9e3691797a92059cab3d212e7b62c0ffbdb49a49947bb712b4da6`
- 输入审计: `docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md`
- Closure review input SHA-256: `aa66a0c1192b0833945b1e833bca2ade307d84e47796eeaf16763e10fe7e6bcc`
- Closure confirmation input SHA-256: `95ca973b7f11d0123b8a92eaa6e85127f576883a96b701f979de31e9a802c925`
- `implementation_allowed=false`, `deployment_allowed=false`, `runtime_action_allowed=false`

## 1. Delta Claim

本 Delta 只补齐已批准 Stage 1.6E-B Design/Plan 已要求、但当前实现遗漏的 authority 和 restart 边界：真实 1.6D trusted-detail linkage、E-A Step-A environment gate、E-A ProfileCore provenance、E-B same-schema attestation，以及 C5/C6/C8/C9 supervisor recovery。

它不修改 Parent Design 字节，不改变 1.6D writer、E-A capability authority、G2 grammar、12 小时窗口、三 symbol 上限、单 active event 或任一权限开关。它不是实现、部署或 runtime 授权。

## 2. Confirmed Facts And Root Cause

1. 1.6D live `DetailRevisionRecord` 的 authoritative fields 是 `source_article_id`、`detail_revision_id`、`detail_raw_sha256`、`raw_payload_relative_path`、`t_detail_trusted_ms`、`captured_at_ms` 和 `record_seq`；它不含 request observation ID。
2. 1.6D writer 以 `datetime.fromtimestamp(now_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")` 形成 daily stream key，并将同一 poll 的 trusted detail observation 写入 `detail_observations/<UTC-date>.jsonl`，随后写入带相同 `captured_at_ms=now_ms` 的 `detail_revisions.jsonl`。
3. 真实 request identity 只在 committed `DetailObservationRecord.request_observation_id` 中；其 trusted linkage 由 source profile、request variant、article ID、raw SHA-256 和 raw relative path 唯一确定。
4. E-A 的 frozen Step-A projection helper 是 `get_vps_step_a_projection(project_root)`。它只能由 E-B composition root 在每一次 environment-gate invocation 中以 side-effect-free 方式调用；不得复制、迁移或由 E-B storage/source/model 重实现。supervisor-root gate 取得的 projection 不得授权之后的 event-root creation。
5. 当前实现把 E-A attestation bytes 复制为 E-B attestation，并且从 offset zero 读取 fresh bootstrap 的历史 revision；这不满足 Parent Design Sections 6.2, 6.2.1, 7.2, 7.3 and 13。
6. 当前 supervisor 没有 C5/C6/C8/C9 recovery gate，terminal 文件的存在会错误释放 global capacity。

## 3. Scope And Non-Goals

### 3.1 In Scope

1. E-B `source.py` 读取并验证 current 1.6D V3 committed stream map，构造 revision-observation-raw 唯一 linkage。
2. E-B composition root 在每个 fresh-root environment gate 调用 frozen E-A Step-A helper 并将该 gate 的 immutable projection 传入 E-B `storage.py`；`storage.py` 验证该 projection、E-A bundle 和 E-B own same-schema environment attestation。
3. E-B supervisor 在 source polling 前执行唯一 recovery sequence。
4. 对 bootstrap、environment、linkage、ProfileCore provenance 和 C5/C6/C8/C9 编写 RED/GREEN failure fixtures。

### 3.2 Non-Goals

1. 修改 1.6D、E-A、G2、shared Stage 1.5 storage guard 或 Parent Design/Plan。
2. 新 adapter、迁移、旧 root repair、manifest retry、并发、queue、retry、第二 window、replay 或 backfill。
3. private/auth/account/order API、alpha、trade signal、paper trading、live trading 或 execution authority。

## 4. Acceptance Invariants

- `INV-R01 Source linkage`: 对每个 revision，唯一合法 observation stream key 是 `detail_observations/` + `utc_date_from_ms(revision.captured_at_ms)` + `.jsonl`；`utc_date_from_ms` 精确等于 Unix milliseconds 经 `datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")`。该 exact key 必须同时存在于 current complete checkpoint 的 `stream_offsets` 与 `stream_last_hashes`，offset 必须大于 zero。E-B 只解析该 key 的 committed bytes `[0, offset)`，其 final line SHA-256 必须等于该 map entry。candidate rows 仅是这些 exact checkpoint-authorized streams 的 committed bytes 并集；禁止 glob、目录/root 扫描、prefix/date inference、fallback 或 uncommitted tail。checkpoint/map/boundary/hash 或 record run/mode/profile/variant validation failure 是 `source_checkpoint_invalid`。在 valid committed checkpoint 后，zero 或 multiple trusted revision-observation linkage 是 `source_structural_failure/orphan_or_ambiguous_live_revision`。两类失败均为零 raw/projection/admission/event/request 和零 consumer-checkpoint advance。
- `INV-R02 Bootstrap`: 不存在 E-B consumer checkpoint 时，只将当前 complete 1.6D boundary durable/read-back 为 bootstrap checkpoint；零历史 raw/projection/admission/event/network。
- `INV-R03 E-A environment`: 每一次 fresh supervisor/event root creation 前，E-B 使用该次 frozen E-A Step-A projection 重算当前 host，并比较 Parent Design 规定的 pre-root stable equality fields。supervisor-root projection 不得复用于 C5 event-root creation。任何 mismatch 是 `environment_attestation_failed`，零该次 E-B root creation、零 source read、零 network。
- `INV-R04 E-B attestation`: 每个 supervisor/event root 写入由当前 E-B runtime/root state 独立重建的 `stage1_6e_a_execution_environment_attestation_v1`。byte equality with E-A is never authority proof and must not arise from copying E-A bytes。`deployment_git_commit` 必须等于独立授权的 E-B commit；receipt 精确绑定两个 read-back SHA-256。
- `INV-R05 C5/C6 ownership`: C5 只可从 exact admitted row 创建唯一 deterministic event root；C6 只可验证该 root 后 checkpoint-only 回填 active fields。错误/多个/foreign/malformed root 不写入、不请求。
- `INV-R06 Terminal capacity`: C8 和 C9 均保留 active fields，禁止 admission/root/HTTP/re-observe/reseal。只有 `valid failed terminal + absent manifest + event writer flock nonblocking acquirable`，或 `valid complete terminal + valid manifest`，才允许释放 capacity。
- `INV-R07 Time immutability`: event window 起点只等于 durable `semantic_projected_at_ms`，在 C5/C6/restart 中永不重新计算。
- `INV-R08 Safety`: `RISK_LIVE_TRADING_ENABLED` 和全部 E-B permissions 永远为 `False`。
- `INV-R09 E-A profile authority`: 四个 base ProfileCore 与其 attestation SHA 只可从已经 `verify_complete_bundle` 成功的 E-A complete bundle 的 exact profile/profile-attestation files 加载；禁止 E-B static fallback ProfileCore、`SHA256(profile_id)` 构造或未验证的 manifest map。derived event ProfileCore 必须绑定其 exact verified base profile attestation SHA。

## 5. Producer / Consumer Contract Matrix

| Producer | Immutable input | E-B consumer | Required validation | Failure |
|---|---|---|---|---|
| 1.6D checkpoint | complete V3 `stream_offsets` / `stream_last_hashes` | `source.py` | exact key resolver, exact map membership, committed boundary/hash, IDs, heartbeat | no new admission |
| 1.6D detail revision | `detail_revisions.jsonl` | `source.py` | exact revision schema and one trusted observation linkage | no projection |
| 1.6D observation | exact `detail_observations/<UTC-date>.jsonl` | `source.py` | run/mode/profile/variant/trust/article/raw SHA/path exact equality | no raw copy |
| E-A root | closed bundle plus attestation/profile files | composition root + `storage.py` | E-A verifier, injected Step-A equality, exact manifest/profile SHA | no E-B root/source read |
| E-B supervisor | checkpoint/admission/event roots | `observer.py` | C5/C6/C8/C9 matrix before source poll | preserve bytes, no HTTP |

## 6. Source State And Failure Semantics

`source.py` must validate every path named by the current complete checkpoint map before reading a revision. A nonzero offset requires a regular, non-symlink file, exact final committed line hash and line-boundary offset. The consumer may use only committed bytes below each declared offset.

For each newly committed revision, E-B derives only the `INV-R01` exact daily key from `revision.captured_at_ms`; it never searches for another observation stream. That key must be committed by the same current checkpoint. It parses only `[0, stream_offsets[key])`, and requires exactly one trusted observation where:

```text
revision.capture_mode == live_observed
revision.source_profile_id == binance_public_web_bapi_en_delisting_catalog_v2
revision.request_variant == bapi_article_detail_query_v1

observation.capture_mode == live_observed
observation.source_profile_id == binance_public_web_bapi_en_delisting_catalog_v2
observation.request_variant == bapi_article_detail_query_v1
observation.run_id == authorized_source_run_id
observation.trust_validation_status == trusted
observation.source_article_id == revision.source_article_id
observation.raw_payload_sha256 == revision.detail_raw_sha256
observation.raw_payload_relative_path == revision.raw_payload_relative_path
```

The projection receives `request_observation_id` from that row and `source_detail_trusted_at_ms` from `revision.t_detail_trusted_ms`. There are no aliases, defaults, inferred IDs, raw paths, timestamps or scan-and-pick fallback.

Checkpoint map membership/boundary/hash failure, or an invalid run/mode/profile/variant record, is `source_checkpoint_invalid`. After those checks pass, zero or multiple matching trusted observations is exactly `source_structural_failure/orphan_or_ambiguous_live_revision`. Neither classification advances the consumer checkpoint or permits raw copy, projection, admission, event-root creation or request.

Fresh bootstrap writes a read-back `source_consumer_checkpoint.json` at the observed boundary, including the actual committed `detail_revisions` last-line hash/sequence when nonzero. It returns before raw copying, parsing, admission or public client construction.

## 7. Environment Authority

For each environment-gate invocation, the E-B composition root obtains exactly one immutable `current_step_a_projection` by side-effect-free call to frozen `get_vps_step_a_projection(project_root)`, then passes that gate-local value to E-B storage/environment validation. E-B `storage.py` must not import an E-A runner module; E-B source/model/storage must not reimplement the projection. If the frozen helper cannot be imported and called without side effects, `STOP = design_decision_required`; implementation may not substitute import relocation, subprocess execution, copied helper or duplicated formula.

Fresh supervisor-root creation uses this exact order:

```text
global coordination precondition
-> verify E-A closed complete bundle
-> recompute exact E-A Step-A projection
-> PRE-ROOT equality gate
-> create fresh E-B supervisor root
-> acquire supervisor writer lock
-> POST-ROOT filesystem equality gate
-> construct/read-back E-B attestation
-> construct/read-back authority receipt
-> recovery
-> source polling
```

PRE-ROOT equality requires `deployment_host_identity`, `project_root_realpath`, `network_namespace_inode`, `proxy_environment` and clean deployment worktree to equal E-A, plus `current.capability_root_parent_filesystem_st_dev == E-A.root_filesystem_st_dev` and `current.shared_lock_filesystem_st_dev == E-A.shared_lock_filesystem_st_dev`. A PRE-ROOT failure performs zero E-B root creation, zero source read and zero network.

Fresh C5 event-root creation independently uses this exact order:

```text
durable admitted row + deterministic missing event root
-> recompute exact E-A Step-A projection
-> PRE-ROOT equality gate
-> create deterministic event root
-> acquire event writer lock
-> POST-ROOT filesystem equality gate
-> construct/read-back event E-B attestation
-> construct/read-back event authority receipt
-> event contract/profile/checkpoint
```

A projection obtained for supervisor-root creation MUST NOT authorize a later event-root creation. An existing C6 root remains governed by the Parent Design's environment/network revalidation rules for resumed roots and later requests.

POST-ROOT equality requires `E-B.root_filesystem_st_dev == current.capability_root_parent_filesystem_st_dev == E-A.root_filesystem_st_dev == E-A.shared_lock_filesystem_st_dev == E-B.global_lock_filesystem_st_dev`. Any post-root mismatch preserves that fresh root as partial/non-consumable, performs zero source read and zero network, and cannot create an attestation or receipt. No supervisor/event terminal with a new `environment_attestation_failed` terminal reason is authorized.

The E-B same-schema attestation is independently reconstructed only after both equality gates. The receipt binds exact E-A and E-B read-back attestation SHA-256 values; it does not use attestation-byte equality as proof.

## 8. Recovery State Machine

Recovery runs after supervisor lock/attestation receipt validation and before source polling.

| State | Required action | Forbidden action |
|---|---|---|
| C5 exact admission, no root, no active fields | validate immutable admission/projection, create exact root, then atomically set same active identities | duplicate admission/root, HTTP before checkpoint |
| C6 exact admission, one owned valid nonterminal root, no active fields | validate contract/profile/checkpoint ownership, checkpoint-only set same active identities | recreate root, HTTP before checkpoint |
| C5/C6 mismatch | preserve all bytes; `global_active_supervisor_state_invalid` | clear/set active fields, HTTP |
| C8 terminal write/read-back failed, terminal absent because persistence failed, or terminal malformed/invalid | retain root and active fields as blocker | new admission/root/HTTP or invented terminal |
| C9 valid complete terminal but absent/invalid manifest | retain root and active fields as blocker | slot re-observation, manifest rewrite, capacity release |
| valid failed terminal, manifest absent, event writer flock nonblocking acquirable | validate terminal, then clear active fields exactly once | manifest creation or admission before lock proof |
| valid failed terminal with writer flock held | retain root and active fields as blocker | capacity release, new admission or HTTP |
| valid complete terminal and closed manifest | validate then clear active fields | reseal/reobserve |

All C5/C6 event contracts set `event_window_started_at_ms=projection.semantic_projected_at_ms`; restart time is never an input.

## 9. Compatibility And Persistence

No migration occurs. A pre-existing E-B root that cannot satisfy the Parent Design exact schemas plus this Delta strengthened validation/recovery invariants is preserved and blocks with `global_active_supervisor_state_invalid`; it is never repaired in place. Sealed manifest roots remain read-only. Delta implementation may add no new runtime artifact or serialized schema version beyond existing Parent Design supervisor/event grammar.

## 10. Verification Requirements

Required RED then GREEN tests:

1. Fresh bootstrap with a nonzero committed revision offset produces checkpoint only and zero raw/projection/admission/event/network.
2. The exact daily-key resolver accepts only `utc_date_from_ms(revision.captured_at_ms)` present in both checkpoint maps with a positive committed offset/final-line hash; missing map entry, zero offset, wrong day/prefix key, uncommitted tail, glob/root scan or date-inference substitute rejects without checkpoint advance.
3. Checkpoint/map/boundary/hash or invalid run/mode/profile/request-variant record rejects as `source_checkpoint_invalid`; with a valid committed checkpoint, missing or duplicate trusted article/raw/path observation rejects as `source_structural_failure/orphan_or_ambiguous_live_revision`. Both cases have zero checkpoint advance/raw/projection/admission/event/request.
4. Every E-A PRE-ROOT host/proxy/parent-device/shared-lock/network/clean-worktree mismatch performs zero E-B root/source/client work. Every POST-ROOT root/global-lock device mismatch creates no attestation/receipt and performs zero source/client work; the root is partial/non-consumable and no new environment terminal reason is written. The test proves independent E-B field provenance and only Parent-approved equality predicates, not byte inequality with E-A.
5. Missing or mutated E-A profile attestation, wrong manifest/profile binding, `SHA256(profile_id)` provenance and absent E-A profile file with static fallback each reject. A derived event core binds the exact verified base profile attestation SHA.
6. C5 creates one root and active checkpoint only after valid root; C6 performs checkpoint-only recovery; all negative ownership fixtures preserve bytes. `test_c5_event_root_recomputes_step_a_and_does_not_reuse_supervisor_projection` proves supervisor projection P0 valid, environment changes, C5 recomputes P1, P1 mismatch yields zero event-root creation and zero event HTTP.
7. C8/C9 retain capacity, create no request/admission/root, never reobserve/reseal. A valid failed terminal releases only when manifest is absent and its event writer flock is acquirable; held writer retains active capacity. Valid complete terminal plus valid manifest clears capacity exactly once.
8. Existing focused E-B, 1.6D, E-A, G2 and safety regression suites pass; `git diff --check` passes.

## 11. Open Questions

None. The Delta remains a draft and requires external review/approval plus its own reviewed Implementation Plan before any code changes.
