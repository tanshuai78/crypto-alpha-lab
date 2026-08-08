# Stage 1.5D Schedule Revision Producer Deployment Checklist

## 1. 默认与初始部署配置 (Default Configuration)

- [ ] `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False` 是 `configs/base.py` 中的唯一配置控制点。
- [ ] 初始部署必须保持 `False`。
- [ ] 所有 `events/*.jsonl` 文件路径必须为未转义的通配符 glob。
- [ ] 不得通过仅测试通过来直接在生产环境使能 `effective_producer_enabled`。

## 2. Part A 消费者前置校验与门禁 (Part A Prerequisite Gate)

- [ ] 运行 Part A 完整验证套件：
  ```bash
  PYTHONPATH=src:. .venv/bin/python -m pytest \
    tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
    tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
    tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
    tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py -q
  ```
- [x] 2026-08-08 已在本地运行上述 Part A 套件并干净通过。下次准备 enablement 前必须在候选提交上重跑一次。
- [x] 已确认当前服务器和本地工作区均没有可验证的历史改期公告原始 payload + 对应 manifest。

### 2.1 没有历史备份时的处理

- [ ] 保持 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False`，不得通过修改 metadata 或配置绕过门禁。
- [ ] 不再搜索、下载或补造旧公告的历史证据。事后下载的官方页面不能证明当时的可见性或关联顺序。
- [ ] 保持 Stage 1.5D 正常采集和 Stage 1.5F 正常观察；producer 关闭不会影响新上线公告。
- [ ] 等待下一次真实的延期、改期或取消公告。届时保存该公告的原始 BAPI payload、同一运行 root 的 request manifest、原始 launch 事件和 revision 关联诊断。

### 2.2 下一次真实改期类公告的核验步骤

#### Part A 消费者验证

在包含真实 fixture 和关联测试的候选提交上，重跑第 2 节的四个 Part A 测试文件，并额外运行 producer/runner 规则测试：

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_schedule_revision_producer.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'schedule_revision or trusted_revision_detail or durable_launch' -q
```

两组测试均须退出码为 `0`。第一组证明 1.5F/1.5G 能安全消费 revision；第二组证明 producer 的分类、关联、全符号原子性、重放去重和 runner transport 未回归。

#### 关联规则验证

在服务器上为新公告设置 revision article ID 和原始 launch article ID；producer 仍保持关闭。以下命令只定位四类证据，不写入任何文件：

```bash
export REVISION_ARTICLE_ID="替换为新的延期/改期/取消公告 ID"
export ORIGINAL_LAUNCH_ARTICLE_ID="替换为该公告明确引用的原始 launch 公告 ID"

find "$STAGE1_5D_EVENTS_OUT/raw_payloads/announcement_detail/$REVISION_ARTICLE_ID" -type f -print
rg -n -m 1 "\"source_article_id\": \"$REVISION_ARTICLE_ID\"" \
  "$STAGE1_5D_EVENTS_OUT"/request_manifest/*.jsonl
rg -n -m 5 "\"supersedes_source_article_id\": \"$ORIGINAL_LAUNCH_ARTICLE_ID\"" \
  "$STAGE1_5D_EVENTS_OUT/formal_launch_identity_index.jsonl"
rg -n -m 5 "$REVISION_ARTICLE_ID" \
  "$STAGE1_5D_EVENTS_OUT"/detail_retry_terminal_diagnostics/*.jsonl
```

通过条件：存在原始 BAPI 文件；manifest 对应行的 `http_status=200`、`payload_trusted=true`，且其 `payload_sha256` 与原始文件 SHA-256 一致；每个受影响 symbol 在 identity index 中恰好一行原始 launch；revision diagnostic 的 candidate 明确列出同一个原始 article ID，且没有 `index_collision`、`orphaned`、`ambiguous`、`out_of_scope` 或 `all_symbols_statement_failure`。producer 关闭时，不应出现正式 revision event row；此时 diagnostic 的 `producer_disabled_or_prerequisites_unmet` 是预期结果。

#### 人工复核和证据提交

- [ ] 阅读官方原始 launch 与 revision BAPI 正文，确认受影响 symbol、revision intent（延期、改期或取消）和新时间（如有）与 diagnostic 一致。
- [ ] 确认原始 launch 的 identity index 在 revision decision time 之前已 durable，且每个 symbol 都是唯一匹配。
- [ ] 将该真实 payload 的 SHA-256、匹配 manifest 字段、两篇 article ID、关联 diagnostic 与人工结论写入一个窄范围 fixture metadata；新增一条只读取该 fixture 的回归测试。
- [ ] 单独提交这份真实样本 fixture、metadata 和测试；不要在该提交中修改 enablement 配置。

### 2.3 当前 producer enablement 仍被代码门禁阻断

当前没有可执行的 enablement 配置提交。`build_schedule_revision_producer_attestation()` 要求运行时 `git rev-parse HEAD` 等于 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA`，但后者写在同一份即将提交的 `configs/base.py` 中，形成无法通过普通提交满足的自指 SHA 条件。

- [ ] 在单独的 attestation hotfix 修复并以真实 Git repository 测试证明该条件可满足前，不得把 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED` 改为 `True`。
- [ ] 在该修复完成后，enablement 必须是第三个独立提交：仅修改门禁配置及其审计记录；部署后检查 `schedule_revision_producer_configured_enabled=true`、`schedule_revision_producer_consumer_prerequisites_verified=true`、`schedule_revision_producer_effective_enabled=true` 和 `schedule_revision_producer_health="ready"`。

## 3. KO/RDDT 只读 Salvage 离线审计命令 (Readonly Salvage Audit Command)

```bash
# All paths must be local copies. This command is readonly against the three
# evidence inputs and writes a separate non-production audit directory.
export LOCAL_EVIDENCE_ROOT="/absolute/path/to/local/evidence"
export STAGE1_5D_EVENTS_GLOB="$LOCAL_EVIDENCE_ROOT/stage1_5d/events/*.jsonl"
export STAGE1_5F_ACCEPTED_GLOB="$LOCAL_EVIDENCE_ROOT/stage1_5f/events_accepted/**/*.jsonl"
export STAGE1_5F_STATE_GLOB="$LOCAL_EVIDENCE_ROOT/stage1_5f/observer_state.jsonl"

PYTHONPATH=src:. .venv/bin/python - <<'PY'
import glob
import hashlib
import json
import os
import time
from pathlib import Path

ARTICLE = "307687ad279e42e6909ee1be8c472b50"
SYMBOLS = ("KOUSDT", "RDDTUSDT")
REQUIRED = ("LOCAL_EVIDENCE_ROOT", "STAGE1_5D_EVENTS_GLOB", "STAGE1_5F_ACCEPTED_GLOB", "STAGE1_5F_STATE_GLOB")
missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
if missing:
    raise SystemExit(f"ERROR: missing required environment variables: {', '.join(missing)}")

root = Path(os.environ["LOCAL_EVIDENCE_ROOT"]).expanduser().resolve()
if not root.is_dir():
    raise SystemExit(f"ERROR: LOCAL_EVIDENCE_ROOT is not a directory: {root}")

def files_for(name):
    paths = [Path(p).resolve() for p in sorted(glob.glob(os.environ[name], recursive=True))]
    if not paths:
        raise SystemExit(f"ERROR: {name} matched zero files")
    for path in paths:
        try:
            path.relative_to(root)
        except ValueError:
            raise SystemExit(f"ERROR: {name} input is outside LOCAL_EVIDENCE_ROOT: {path}")
        if not path.is_file():
            raise SystemExit(f"ERROR: {name} matched a non-file: {path}")
    return paths

input_files = {name: files_for(name) for name in REQUIRED[1:]}

def read_rows(paths):
    rows = []
    for path in paths:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                rows.append((path, line_no, json.loads(line)))
    return rows

def canonical_sha(row):
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def row_record(path, line_no, row):
    return {
        "path": str(path),
        "line_number": line_no,
        "canonical_row_sha256": canonical_sha(row),
    }

source_rows = read_rows(input_files["STAGE1_5D_EVENTS_GLOB"])
accepted_rows = read_rows(input_files["STAGE1_5F_ACCEPTED_GLOB"])
state_rows = read_rows(input_files["STAGE1_5F_STATE_GLOB"])
errors, selected = [], {}

def symbols_of(row):
    return {str(x).upper() for x in row.get("symbols", [])} | ({str(row.get("symbol", "")).upper()} if row.get("symbol") else set())

for symbol in SYMBOLS:
    source_hits = [(p, n, r) for p, n, r in source_rows if r.get("source_article_id") == ARTICLE and symbol in symbols_of(r)]
    accepted_hits = [(p, n, r) for p, n, r in accepted_rows if r.get("source_article_id") == ARTICLE and r.get("symbol") == symbol]
    if len(source_hits) != 1:
        errors.append(f"{symbol}: expected exactly one source row, found {len(source_hits)}")
        continue
    if len(accepted_hits) != 1:
        errors.append(f"{symbol}: expected exactly one accepted row, found {len(accepted_hits)}")
        continue
    source = source_hits[0]
    accepted = accepted_hits[0]
    event_id = accepted[2].get("event_id") or source[2].get("event_id")
    states = [(p, n, r) for p, n, r in state_rows if r.get("event_id") == event_id and r.get("symbol") == symbol]
    if not states:
        errors.append(f"{symbol}: missing state for event_id={event_id}")
        continue
    state = states[-1]  # observer_state is append-only; the last matching row is the latest state.
    src, acc, st = source[2], accepted[2], state[2]
    checks = (
        src.get("formal_event_contract_version") == 2,
        acc.get("formal_event_contract_version") == 2,
        st.get("anchor_contract_version") == 2,
        src.get("source_contract_status") == "formal_v2_valid",
        acc.get("source_contract_status") == "formal_v2_valid",
        src.get("launch_anchor_evidence_level") == "official_schedule",
        acc.get("launch_anchor_evidence_level") == "official_schedule",
        acc.get("effective_observation_anchor_source") == "official_schedule_anchor",
        src.get("anchor_precedence_policy") == "official_schedule_priority_v1",
        acc.get("anchor_precedence_policy") == st.get("anchor_precedence_policy") == "official_schedule_priority_v1",
        bool(src.get("source_anchor_contract_hash")),
        src.get("source_anchor_contract_hash") == acc.get("source_anchor_contract_hash") == st.get("source_anchor_contract_hash"),
        bool(acc.get("source_anchor_contract_hash")),
        acc.get("source_anchor_contract_hash") == st.get("source_anchor_contract_hash"),
        bool(acc.get("admission_anchor_contract_hash")),
        acc.get("admission_anchor_contract_hash") == st.get("admission_anchor_contract_hash"),
        bool(st.get("latest_anchor_contract_hash")),
        st.get("latest_anchor_evidence_level") == "official_schedule",
        st.get("latest_max_evidence_class") == "clean_or_recovery",
        not st.get("observation_anchor_revision_contaminated"),
    )
    if not all(checks):
        errors.append(f"{symbol}: formal v2 lineage is incomplete or mismatched")
        continue
    selected[symbol] = {"source": row_record(*source), "accepted": row_record(*accepted), "latest_state": row_record(*state)}

decision = "stage1_5g_formal_lineage_salvage_audit_pass" if not errors and len(selected) == len(SYMBOLS) else "stage1_5g_formal_lineage_salvage_audit_failed"
output = root / "stage1_5g" / "reviews" / f"ko_rddt_lineage_salvage_{int(time.time())}"
output.mkdir(parents=True, exist_ok=False)
manifest = {
    "decision": decision,
    "salvage_mode": "readonly_lineage_reconciliation",
    "nonproduction_audit_only": True,
    "target_article_id": ARTICLE,
    "target_symbols": list(SYMBOLS),
    "created_at_ms": int(time.time() * 1000),
    "input_files": {name: [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths] for name, paths in input_files.items()},
    "selected_rows": selected,
    "errors": errors,
}
(output / "formal_lineage_salvage_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
(output / "formal_lineage_salvage_report.md").write_text(f"# KO/RDDT Readonly Lineage Salvage Audit\n\nDecision: `{decision}`\n\nErrors: `{len(errors)}`\n", encoding="utf-8")
print(json.dumps({"decision": decision, "output": str(output), "errors": errors}, indent=2))
raise SystemExit(0 if decision.endswith("_pass") else 1)
PY
```

## 4. 运行证明与生效要求 (Attestation & Health Check)

- [ ] 检查 `live_safety_gate_summary.json` 中的字段：
  - `schedule_revision_producer_supported == true`
  - `schedule_revision_producer_configured_enabled == false`
  - `schedule_revision_producer_effective_enabled == false`
  - 初始部署时 `schedule_revision_producer_consumer_prerequisites_verified` 仅记录真实前置证据；未记录时必须为 `false`，不得用测试结果伪造为 `true`。
- [ ] 只有显式配置为 `true`，且 commit、Part A suite、真实改期类 fixture 与当前 poll integration health 均已验证时，才允许 `schedule_revision_producer_effective_enabled == true`。
- [ ] 如需跨 root 关联，只能显式传入经 SHA-256 验证的 `--formal-launch-identity-index-snapshot`；缺失或无效 snapshot 仅阻断 revision，不得阻断正常 launch。
- [ ] 确认非生产环境只读 salvage 不改写 1.5F 生产 root。
- [ ] 确认生产可执行日志中无全局 exception 或 tracebacks。
