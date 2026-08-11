# Stage 1.5D Schedule Revision Producer Git Ancestry Attestation Design

**日期：** 2026-08-10
**状态：** design draft，待独立审查
**关联：** [2026-08-04 Schedule Revision Producer Rules Design](2026-08-04-external-signal-shadow-lab-stage1-5d-schedule-revision-producer-rules-design_CN.md) Section 5.3
**范围：** 仅修复 producer enablement 的 Git attestation 自指缺陷；不启用 producer，不改变 revision producer 的业务规则。

---

## 1. Confirmed Facts

1. `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False`，当前生产行为保持 producer disabled。
2. 当前 attestation 要求 `current_commit_sha == EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA`。
3. prerequisite SHA 写入 `configs/base.py` 后形成新的 Git commit；新 commit 的 `HEAD` 必然不同于被写入的 prerequisite SHA。因此该条件无法用于“先验证代码、再单独提交 enablement 配置”的正常流程。
4. `build_schedule_revision_producer_attestation()` 由 Stage 1.5D runner 在启动、poll ready 和 summary/runtime-gate 写出前调用；其结果控制 formal schedule revision 是否可 emit。
5. 现有测试仅以相等/不等的字符串模拟 SHA，未验证真实 Git ancestor 关系、工作树一致性或运行中 `HEAD` 漂移。
6. 本地当前仓库使用 Git SHA-1 object format 且非 shallow；部署环境仍必须在运行时独立验证，不能假定与本地相同。
7. 当前部署以 `rsync` 同步工作树。故 `HEAD` 可以指向一个提交，而 Python 实际从被同步但未提交的文件加载代码；仅验证 `HEAD` 不足以证明实际运行代码。

---

## 2. Core Issue

当前规则将“已验证的 producer 代码提交”与“当前运行的部署提交”误建模为必须相同。

```text
verified proof commit A
write A into enablement config and commit
current deployment commit B

old gate: A == B   -> false
```

将比较改为 `A` 是 `B` 的 ancestor 是必要条件，但不是充分条件：`A` 之后的提交可能修改、回退或删除 producer 关键代码；部署工作树也可能与 `HEAD` 不同。本设计因此验证以下三件相互独立的事实：

1. 运行仓库是可验证、非 shallow 的 Git SHA-1 repository。
2. proof commit `A` 到启动 commit `B` 之间，受保护的 producer runtime 代码未变。
3. 进程实际加载的受保护工作树与启动 commit `B` 一致，且运行期间 `HEAD` 未漂移。

直接移除 SHA 检查或只保留 ancestor 检查均会降低 enablement 门槛，不可接受。

---

## 3. Scope And Non-Goals

### 3.1 In Scope

1. 将 prerequisite commit 的验证从 equality 升级为 Git ancestry、受保护代码树等价和字段级 config delta 验证。
2. 验证启动时工作树与 `HEAD` 一致，并在每个 poll 验证 `HEAD` 未相对启动快照漂移。
3. 对 Git 缺失、错误 repository、SHA-256 object format、浅历史、未知 commit、非祖先、代码差异、非 allowlist config delta、dirty/untracked runtime Python 文件、模块路径遮蔽和 Git 超时实施 fail-closed。
4. 用真实临时 Git repository 覆盖 A -> B allowlisted-config enablement、producer/consumer 代码变化、dirty worktree、shallow repository 和运行中 `HEAD` 漂移的回归测试。
5. 为 Stage 1.5D/1.5F 增加仅用于 attestation 的同一上游 root binding、root-contract/summary metadata、atomic summary publish、consumer runtime sticky latch 和 process identity；不改变其 revision application 或 depth observation 业务语义。
6. 保持默认 producer disabled 行为与交易权限不变。

### 3.2 Explicit Non-Goals

1. 不将 `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED` 改为 `True`。
2. 不修改 revision classifier、linking、identity index、formal revision JSONL schema 或 Stage 1.5G 代码。Stage 1.5F 仅允许本设计定义的 runtime attestation、root-contract/summary metadata、atomic publish 和 sticky latch 改动。
3. 不建立 CI、签名服务、外部数据库、tag policy、运行时动态 import graph 或独立的 attestation artifact/schema。测试期使用 Python 标准库 `ast` 检查静态本地 import closure 不属于运行时机制；本设计仅扩展既有 Stage 1.5F root contract/summary 的 metadata。
4. 不以 synthetic fixture 取代真实延期/改期/取消公告的 enablement 证据。
5. 不将 Part A / real fixture 的人工配置 flag 伪装为 cryptographic proof；它们仍是独立的运营证明与独立复核门槛。
6. 不修改 live/paper/execution/alpha 的只读安全边界。
7. 不修改 Stage 1.5F revision application semantics、depth observation timing、clean/recovery classification、snapshot collection 或风险/交易权限。

---

## 4. Decision

保留现有配置名：

```text
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA
```

其新语义为：**已验证 proof commit `A` 必须是本进程启动 commit `B` 的 ancestor，且 `A` 与 `B` 的受保护 producer/consumer runtime 树必须最终内容等价。**

```text
proof commit A
config-only enablement commit B

ancestor(A, B) = true
protected_runtime_tree(A) == protected_runtime_tree(B)
config_delta(A, B) in explicit_allowlist
startup_worktree_matches(B) = true
```

`configs/base.py` 不再整体豁免。`A -> B` 仅允许其四个 attestation assignment 变化：

```text
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED
```

字段级比较不得删除 allowlisted assignment。`A` 和 `B` 都必须恰有一次位于相同 module `body` index 的 `ast.Assign`，target 必须恰为一个同名 `ast.Name`，且不得使用 `AnnAssign`、multi-target、tuple target 或复合 assignment。比较时保留整个 assignment node、target 与 module 内顺序，仅将其 RHS 规范化为固定 sentinel；规范化后的完整 module AST 必须相同。

四个 RHS 都必须为 `ast.Constant` literal：prerequisite 必须为 `str`，其余三个必须为 `bool`。不允许 call、name、attribute、subscript、walrus、binop、boolop、环境变量或任何其他表达式。runtime 仍独立验证 prerequisite SHA 的格式和 Git commit 身份。

该规则允许专门的 enablement commit，但禁止其夹带 lookback、retry/fairness/anchor/runtime-gate 阈值、任何风险开关或动态配置逻辑。启动工作树仍须相对 `B` clean；未提交或直接同步的配置改动同样 fail-closed。

本设计不升级 schedule revision transport。当前事实为：`FORMAL_EVENT_CONTRACT_VERSION_V2 = 2`，`FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION = 2`；Stage 1.5F root contract 允许 revision versions `[1, 2]` 以兼容历史 artifact，但本 producer 只可发 version `2`。因此 enablement consumer capability 必须同时声明 formal event version `2` 与 formal schedule revision version `2`。

### 4.1 Fixed Protected Runtime Path Manifest

本修补在既有 runner 脚本中定义一个固定、可审计的路径清单；不新建 `src/` helper 或在 runtime 动态解析 import graph。清单覆盖会改变 revision candidate 输入、formal row 构造/写入、attestation、revision 消费/lineage 或 runtime-gate/review 表述的现有运行路径。

**Stage 1.5D producer paths：**

```text
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
src/research/external_signal_shadow/stage1_5d_live_event_source_client.py
src/research/external_signal_shadow/stage1_5d_live_event_source_collector.py
src/research/external_signal_shadow/stage1_5d_live_event_source_evidence.py
src/research/external_signal_shadow/stage1_5d_live_event_source_first_bar.py
src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py
src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py
src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py
src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
src/research/external_signal_shadow/stage1_5d_schedule_revision_producer.py
src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py
src/research/external_signal_shadow/stage1_5_launch_event_contract.py
src/research/external_signal_shadow/stage1_5d_runtime_gate.py
```

**Stage 1.5F/1.5G consumer-lineage paths：**

```text
scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_budget.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_client.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_metrics.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py
src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
src/risk/limits.py
```

`stage1_5_launch_anchor_contract.py` 和 `stage1_5_launch_event_contract.py` 同时属于 producer/consumer shared contract，已在上表保护。`configs/base.py` 使用本节的字段级规则而非普通 path diff。

清单是安全控制，而非全仓库 freeze。无关文档、测试和 `data/` 改动不阻止已证明 producer 的 config-only enablement；但影响 formal revision 被 1.5F 应用或被 1.5G 判定 lineage 的 1.5F/1.5G 改动不是无关改动。每一个清单 path 必须在 `A` 和 `B` 都存在且为 tracked blob；拼错、缺失或删除 path 一律 fail-closed。未来接入新的本地 runtime dependency 时，接入代码本身会改变受保护入口路径，故必须先建立新的 proof commit，并在经批准的后续设计/计划中更新此清单。

测试期使用标准库 `ast` 递归解析上述 1.5D/1.5F/1.5G 入口的项目内 import closure，断言所有可解析的本地 Python dependency 都在 protected manifest 或 `configs/base.py` 特殊 config 规则内。relative import 也必须解析。受保护路径中任何 `importlib.import_module`、`__import__`、`exec` 或 `eval` 均为 fail-closed，除非后续经独立设计明确加入固定 target 的 allowlist；当前 allowlist 为空。该测试不在 poll 中运行；标准库和第三方 packages 不在 Git path proof 范围内。

`CRITICAL_RUNTIME_MODULES` 不是人工挑选的子集：它等于各进程入口的静态 project-local closure，加上 `configs.base` 和 `src.risk.limits`。Stage 1.5D 只验证 producer closure；Stage 1.5F 在启动时以固定 closure import 并验证 consumer closure。每个 critical module 的 `module.__file__` 都必须 resolve 到其 manifest path，或对 `configs.base` resolve 到受字段级规则保护的 `configs/base.py`，不能只验证少量“明显”模块。

### 4.2 Root Identity And Canonical Hash Contracts

Stage 1.5D output root、Stage 1.5F input root 和 Stage 1.5F output root 全部使用同一个固定 root-ID 函数：

```python
def canonical_root_id(path: str | Path) -> str:
    canonical_path = str(Path(path).resolve())
    return hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()
```

该函数不接受 operator 直接提供的 ID。Stage 1.5D 从自身 `--output-root` 派生 `stage1_5d_output_root_id` 并写入 runtime gate；Stage 1.5F 从 `--stage1-5d-events-glob` 派生 events root、从已验证 runtime-gate 的 `source_root` 派生 gate root，并在 root contract 中写出：

```text
source_stage1_5d_output_root_id
source_stage1_5d_events_root_id
source_stage1_5d_runtime_gate_root_id
```

Stage 1.5F 只在三个 ID 相等、runtime-gate 的 `source_root` 与 events-glob 派生 root 相等、且 runtime-gate 文件本身是该 root 的 `live_safety_gate_summary.json` 时，将 consumer static attestation 写为 true。无法建立该绑定时，root contract 仍可作为普通 observer artifact 写出，但 attestation 必须为 false；不得阻断既有 normal launch/depth observation。

两类 SHA-256 contract 必须分离，禁止复用或混写 serialization：

```python
def canonical_manifest_sha256(policy_version: str, paths: Iterable[str]) -> str:
    payload = policy_version + "\n" + "\n".join(sorted(paths)) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def canonical_root_contract_sha256(root_contract: dict) -> str:
    payload = json.dumps(
        root_contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
```

manifest paths 必须是 POSIX relative paths；root-contract hash 不依赖 pretty-print、filesystem separator 或 key insertion order。root contract 不得写入自己的 hash，也不得包含 heartbeat、summary 或其他可变 runtime field；summary 只保存 `consumer_root_contract_sha256`。

### 4.3 Why No External Signature Or CI Artifact

Git 的 object、ancestry、path diff 和工作树检查足以解决当前自指与 rsync 风险。外部签名或 CI artifact 不能以更小的改动解决这些问题，且目前没有可靠的部署基础设施可消费，故不引入。

---

## 5. Acceptance Invariants

| ID | Invariant |
|---|---|
| `INV-A1` | `prerequisite_commit_sha` 必须是当前仓库 SHA-1 格式的完整 40 位十六进制 commit SHA；空值、缩写、非法值和 SHA-256 repository 均不得满足 prerequisite。 |
| `INV-A2` | attestation 只能从 runner 文件所在 repository 内部派生 `startup_head_sha`；调用者不得传入或覆盖 `current_commit_sha`。 |
| `INV-A3` | repository 必须是可用 work tree、`show-toplevel` 与 runner source root 一致、object format 为 `sha1`、`is-shallow-repository` 为 `false`，且 prerequisite 与 startup `HEAD` 都是 commit object。任一条件失败为 false。 |
| `INV-A4` | `git merge-base --is-ancestor prerequisite startup_head` 必须返回 0；每个 manifest path 必须在 `A`/`B` 均为 tracked blob，且 `git diff --quiet prerequisite startup_head -- protected_runtime_paths` 返回 0。该 diff 的精确定义是最终内容等价：中间提交曾改动但在 `B` 完全恢复为 `A` 内容时可通过。相等 SHA 仍是合法 ancestor，但不是唯一合法状态。 |
| `INV-A5` | `configs/base.py` 的 `A -> B` AST delta 只能涉及 Section 4 所列四个、各恰一次、位置不变且 target 不变的 top-level `ast.Assign`。比较完整 module AST 时仅规范化这四个 literal RHS；新增、删除、移动、重复、复合或动态 assignment 均 fail-closed。`RISK_LIVE_TRADING_ENABLED` 在当前运行模块中必须仍为 `False`。 |
| `INV-A6` | 启动时，受保护路径及 `configs/base.py` 的 staged/unstaged tracked diff 必须均相对 `HEAD` 为空；`configs/`、`scripts/external_signal_shadow/`、`src/research/external_signal_shadow/` 和 `src/risk/` 中不得有可导入的 untracked 或 ignored `.py` 文件。无关 `data/`、review output 和其他不受保护路径不参与该检查。 |
| `INV-A7` | `CRITICAL_RUNTIME_MODULES` 必须由静态 closure 完整派生。每个 critical local module 的 `module.__file__` 都必须 resolve 到对应 manifest repository path；外部 `PYTHONPATH` shadow、closure 漏项或未批准 dynamic import 仅能导致 producer fail-closed。 |
| `INV-A8` | Stage 1.5F 必须自行写出 fresh runtime consumer attestation，证明其进程启动于与 Stage 1.5D `startup_head_sha` 相同的 commit、consumer closure 路径有效、formal schedule revision v2 可消费且当前未被 sticky compromise。Stage 1.5D 只在该 attestation fresh/ready 时可 effective enable。 |
| `INV-A9` | 进程保存不可变 `startup_head_sha` 和 `runtime_attestation_compromised = false`。启动后任一次 `HEAD` drift、protected worktree/untracked Python/module-path failure 或 poll budget timeout 都必须将 latch 置为 true；consumer runtime failure 仅在 `producer_armed_once = true` 后置 latch。同一进程中它不得恢复，唯有重启后重新完整验证。 |
| `INV-A14` | Stage 1.5F 的 events-glob root、runtime-gate `source_root` 和 attested source output root 必须是同一 canonical Stage 1.5D root；Stage 1.5D 只接受其 `source_stage1_5d_output_root_id` 等于自身 output root ID 的 fresh consumer proof。Stage 1.5D restart 保持同一 output root 时不改变该 binding。 |
| `INV-A15` | manifest hash 与 root-contract hash 使用 Section 4.2 两套不同且固定的 canonicalization。summary 的 root-contract hash 必须严格等于当前 root contract 的 canonical JSON hash；任一 root-contract attestation field 变化都必须改变该 hash。 |
| `INV-A10` | `effective_enabled` 仍要求 configured flag、Git/代码/config/工作树/module-path prerequisite、1.5F runtime consumer prerequisite、Part A suite flag、真实 revision fixture flag 和 `integration_health == ready` 全部为 true。 |
| `INV-A11` | 任一 prerequisite 不满足时，只禁止 formal revision emission；normal launch collection、Stage 1.5D READY 和 Stage 1.5F 消费能力不得被阻断。 |
| `INV-A12` | 本次部署后默认 `configured_enabled = false`、`effective_enabled = false`；本修补不得自动开启 producer。 |
| `INV-A13` | `RISK_LIVE_TRADING_ENABLED = False` 及 trade/paper/live/execution/alpha permissions 必须保持 false。 |

---

## 6. Producer Attestation Contract

### 6.1 Implementation Boundary And Inputs

Stage 1.5D Git/static proof、producer lifecycle 和 consumer-gate reader 保留在 `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`；Stage 1.5F consumer static/runtime proof 与 metadata publish 保留在 `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` 及其既有 summary/root-contract writer。两者只服务于各自 runner；不新建共享 `src/` attestation module。

公开的 `build_schedule_revision_producer_attestation()` 不再接受 `current_commit_sha`、`repository_path` 或 Stage 1.5D root ID。它只接受既有 reducer 所需的运行健康状态；repository root 从 runner 文件的确定路径内部推导，`startup_head_sha` 从本进程启动快照读取，`stage1_5d.self_output_root_id` 从本进程 `--output-root` 按 Section 4.2 派生。config delta validation 使用 Python 标准库 `ast` 比较 Git 中 `A:B:configs/base.py` 的 source text，不执行这两个历史版本。

```text
configured_enabled                 # config operator attestation
prerequisite_commit_sha            # config operator attestation
part_a_suite_passed                # config operator attestation
real_fixture_verified              # config operator attestation
integration_health                 # existing runtime input
startup_head_sha                   # internally captured at process startup
current_head_sha                   # internally re-read for each reducer call
repository facts / worktree facts  # internally derived only
stage1_5f_consumer_root_contract   # explicit runtime input; optional during bootstrap, required to arm
stage1_5f_consumer_summary         # explicit runtime input; optional during bootstrap, required to arm
stage1_5d.self_output_root_id       # internally derived from this runner's --output-root
```

Part A 和真实 fixture flag 不是 Git cryptographic proof；它们继续表示已完成的人工/流程前提。启用 producer 前仍必须由独立复核确认相应测试、真实原始证据和 config commit，而不能只依赖这些布尔值。

### 6.2 Repository And Git Command Rules

所有 Git subprocess 都使用 `shell=False`、runner repository 作为 `cwd`、`GIT_NO_REPLACE_OBJECTS=1` 和小的固定 timeout。命令异常、timeout、非预期 stdout 或 return code 都只产生 false/diagnostic，不得中止 collector。

```text
git rev-parse --is-inside-work-tree                 -> must be true
git rev-parse --show-toplevel                       -> must equal derived runner repository root
git rev-parse --show-object-format                  -> must be sha1
git rev-parse --is-shallow-repository               -> must be false
git rev-parse --verify HEAD^{commit}                -> startup/current HEAD must be commit
git cat-file -e <prerequisite>^{commit}             -> prerequisite must be commit
git merge-base --is-ancestor <prerequisite> <head>  -> only return code 0 passes
git cat-file -t <prerequisite>:<protected-path>     -> every path must be blob at A
git cat-file -t <head>:<protected-path>             -> every path must be blob at B
git diff --quiet <prerequisite> <head> -- <protected paths>
git show <prerequisite>:configs/base.py             -> AST config delta source A
git show <head>:configs/base.py                     -> AST config delta source B
git diff --quiet HEAD -- <protected paths plus configs/base.py>
git diff --cached --quiet HEAD -- <protected paths plus configs/base.py>
git ls-files --others -- <protected runtime source dirs>
git ls-files --others --ignored --exclude-standard -- <protected runtime source dirs>
```

`is-shallow-repository != false` 在调用 `merge-base` 前直接 fail-closed；不依赖不同 Git 版本对 shallow `merge-base` exit code/stderr 的差异，也不在运行时执行 `git fetch --deepen`。

两个 `git ls-files` 检查的结果仅在含 `.py` 文件时失败：前者覆盖普通 untracked 文件，后者覆盖被 `.gitignore` 忽略的文件。它们防止 rsync 或路径遮蔽放入未追踪 runtime Python 代码；不因 data artifact、JSONL 或 review 文件而拒绝 producer。

进程启动时执行一次完整 repository/proof/config/module-path validation，并将结果冻结为 `startup_static_proof_verified`；该值在本进程内不重新计算，故启动证明失败只能经校正后重启重新验证。启动 full proof 的固定总预算为 10 seconds。每个 poll 不重复 ancestor、manifest blob、`A/B` tree diff 或 AST 比较；只执行 `HEAD` stability、staged/unstaged tracked protected-worktree 和 untracked/ignored Python 检查，固定 aggregate budget 为 1 second。poll budget 用尽或任一检查失败只关闭 producer，不得延迟或阻断正常 announcement collection。

### 6.3 Stage 1.5F Runtime Consumer Prerequisite

Stage 1.5D 的磁盘 proof 不证明 Stage 1.5F 的内存进程，也不能证明当前读取的 summary 属于预期 consumer process。故 1.5F 在启动时必须以自身 consumer closure 建立 runtime attestation，并写入既有 `observer_root_contract.json`；每次 heartbeat/summary 原子更新当前 runtime 状态。它不读取 producer config，也不产生交易权限。

```text
observer_root_contract.json (startup-static, non-control fields)
  consumer_root_id
  consumer_startup_commit_sha
  consumer_static_attestation_verified
  consumer_runtime_manifest_sha256
  source_stage1_5d_output_root_id
  source_stage1_5d_events_root_id
  source_stage1_5d_runtime_gate_root_id
  schedule_revision_consumer_supported = true
  formal_event_contract_versions_allowed contains 2
  formal_schedule_revision_contract_versions_allowed contains 2

live_depth_observer_summary.json (fresh runtime fields)
  consumer_root_id
  consumer_process_instance_id
  consumer_process_started_at_ms
  consumer_startup_commit_sha
  consumer_runtime_manifest_sha256
  consumer_root_contract_sha256
  consumer_runtime_attestation_verified
  consumer_runtime_attestation_compromised
  last_heartbeat_at_ms
  block_new_event_admission
  blocker
```

`consumer_root_id`、三个 `source_stage1_5d_*_root_id` 和 Stage 1.5D 的 `stage1_5d_output_root_id` 都由 Section 4.2 的 canonical root-ID 函数确定；`consumer_process_instance_id` 由每次 1.5F process startup 新生成的 UUID；`consumer_root_contract_sha256` 严格使用 Section 4.2 的 canonical JSON 算法。`consumer_runtime_manifest_sha256` 严格使用 Section 4.2 的 manifest 算法；两者不得共用 helper 或 payload。

1.5F 的 static proof 使用相同的 consumer manifest，要求启动 `HEAD`、clean consumer worktree、无 untracked/ignored runtime Python、完整 consumer critical-module paths 和 `RISK_LIVE_TRADING_ENABLED = False`。其运行中 failure 也使用 sticky latch，不能在同一进程恢复。summary 必须经 temporary file、flush/close 和 `os.replace()` 原子发布，避免 Stage 1.5D 读取半写 JSON。

`consumer_process_instance_id`、`consumer_process_started_at_ms` 和 `consumer_startup_commit_sha` 在一个 1.5F 进程内不可变；root contract/summary 的 identity 字段不一致、contract hash 不匹配或解析失败均为 invalid consumer proof。

当且仅当以下全部成立时，Stage 1.5D 的 `consumer_runtime_prerequisite_verified = true`：

```text
configured_enabled
AND explicit root-contract/summary paths are readable
AND root_mode == v2_production
AND root_contract.consumer_root_id == summary.consumer_root_id
AND summary.consumer_root_contract_sha256 == canonical_root_contract_sha256(root_contract)
AND summary.consumer_startup_commit_sha == stage1_5d.startup_head_sha
AND summary.consumer_process_started_at_ms > 0
AND summary.consumer_process_started_at_ms <= summary.last_heartbeat_at_ms
AND summary.last_heartbeat_at_ms <= now_ms + allowed_clock_skew_ms
AND consumer_static_attestation_verified
AND summary.consumer_runtime_manifest_sha256 == expected_consumer_manifest_sha256
AND root_contract.source_stage1_5d_events_root_id
    == root_contract.source_stage1_5d_runtime_gate_root_id
    == root_contract.source_stage1_5d_output_root_id
AND root_contract.source_stage1_5d_output_root_id == stage1_5d.self_output_root_id
AND schedule_revision_consumer_supported
AND allowed formal event versions contain 2
AND allowed formal schedule revision versions contain 2
AND summary is fresh under the existing runtime-gate staleness bound
AND consumer_runtime_attestation_verified
AND NOT consumer_runtime_attestation_compromised
AND block_new_event_admission == false
AND blocker is empty
```

`allowed_clock_skew_ms` 固定为内部常量 `1_000`，不是 operator 配置；真正的 freshness 仍使用既有 runtime-gate staleness bound。Stage 1.5D runtime gate 同时写出自身 `stage1_5d_output_root_id`，供 1.5F 将 gate 的 `source_root`、gate path 和 events-glob root 建立为同一 binding。

首次 arm 前，上述 predicate 只验证一个可用 consumer candidate。Stage 1.5D 第一次成功 arm producer 时冻结该 candidate 的 `consumer_root_id` 和 `consumer_process_instance_id` 为 `expected_consumer_root_id` / `expected_consumer_process_instance_id`。ARMED 后还必须满足：

```text
summary.consumer_root_id == expected_consumer_root_id
AND summary.consumer_process_instance_id == expected_consumer_process_instance_id
```

此后 1.5F restart 即使使用相同 commit、manifest 或 root，process instance ID 也会改变，必须触发 Stage 1.5D sticky compromise。

当 `configured_enabled = false` 时，Stage 1.5D 不读取该 1.5F input，保持当前默认部署兼容性。configured true 但尚未 arm 时，这两个 path 可以为空并进入 bootstrap waiting；它们在第一次 arm 前必须同时显式提供、可读且通过上述完整验证。具体 bootstrap/armed 生命周期见 Section 8；不得用人工启动顺序替代此 runtime gate。

### 6.4 Reducer Sequence

```text
repository_capable =
  valid_runner_repository()
  AND sha1_object_format()
  AND repository_is_not_shallow()
  AND startup_head_is_commit()

startup_static_proof_verified =  # computed once at process startup; immutable thereafter
  repository_capable
  AND valid_full_sha1(prerequisite_commit_sha)
  AND prerequisite_is_commit()
  AND git_merge_base_is_ancestor(prerequisite_commit_sha, startup_head_sha)
  AND protected_manifest_paths_are_tracked_at_both_commits()
  AND protected_runtime_tree_equivalent(prerequisite_commit_sha, startup_head_sha)
  AND allowed_config_delta_only(prerequisite_commit_sha, startup_head_sha)
  AND startup_protected_worktree_matches_head()
  AND startup_has_no_untracked_runtime_python()
  AND startup_critical_imports_resolve_to_expected_repository_paths()
  AND startup_live_trading_switch_is_false()

runtime_local_verified =
  current_head_sha == startup_head_sha
  AND protected_tracked_worktree_matches_head()
  AND no_untracked_runtime_python()
  AND critical_imports_resolve_to_expected_repository_paths()

consumer_candidate_verified =
  stage1_5f_consumer_runtime_attestation_is_fresh_and_compatible()

consumer_runtime_prerequisite_verified =
  consumer_candidate_verified
  AND (
    NOT producer_armed_once
    OR consumer_identity_matches_frozen_expectation()
  )

non_health_prerequisites_verified =
  startup_static_proof_verified
  AND runtime_local_verified
  AND consumer_runtime_prerequisite_verified
  AND part_a_suite_passed
  AND real_fixture_verified

prerequisites_now_valid =
  non_health_prerequisites_verified
  AND integration_health == "ready"

if not configured_enabled:
  lifecycle = DISABLED
  effective_enabled = false
elif runtime_attestation_compromised:
  lifecycle = COMPROMISED
  effective_enabled = false
elif prerequisites_now_valid:
  if not producer_armed_once:
    freeze_expected_consumer_identity()
    producer_armed_once = true
  lifecycle = ARMED
  effective_enabled = true
else:
  lifecycle = BOOTSTRAP_WAITING_FOR_CONSUMER
  effective_enabled = false

schedule_revision_producer_consumer_prerequisites_verified =
  NOT runtime_attestation_compromised
  AND non_health_prerequisites_verified
```

启动后 local runtime predicate 首次失败时，或 producer 已 arm 后 consumer predicate 首次失败时：

```text
runtime_attestation_compromised = true
effective_enabled = false for the remainder of this process
```

在 `producer_armed_once = false` 时，consumer 缺失、尚未 fresh 或尚未建立 identity 只产生 `BOOTSTRAP_WAITING_FOR_CONSUMER`，不得置 latch。这打破启动循环：E0 的 1.5D 可先正常采集，E1 的 1.5F 可验证上游 gate，E2 重启 1.5D 后才第一次 arm producer。

该 latch 覆盖 Stage 1.5D filesystem/head/module/budget 失败，以及 ARMED 后的 1.5F runtime prerequisite 失败；后续文件恢复、HEAD 回退或 consumer summary 恢复均不得清除。

### 6.5 Health Precedence

为避免 disabled 状态误报为 Git 异常，health reducer 使用固定顺序：

```text
if not configured_enabled:
    producer_disabled
elif runtime_attestation_compromised or not non_health_prerequisites_verified:
    prerequisites_unmet
elif integration_health != "ready":
    existing integration non-ready health
else:
    ready
```

本次不新增 health enum。Git/working-tree/head-drift 细节写入既有 diagnostic/summary context；对下游仍以 `prerequisites_unmet` 表示 fail-closed。

### 6.6 Output Compatibility

以下既有 Stage 1.5D runtime-gate 字段保持名称、布尔语义和 fail-closed 默认值不变：

```text
schedule_revision_producer_supported
schedule_revision_producer_configured_enabled
schedule_revision_producer_consumer_prerequisites_verified
schedule_revision_producer_effective_enabled
schedule_revision_producer_health
```

新增仅供审计解释的非控制字段：

```text
Stage 1.5D runtime gate
  schedule_revision_producer_attestation_policy = git_ancestry_protected_tree_config_consumer_v2
  schedule_revision_producer_protected_manifest_sha256
  stage1_5d_output_root_id

Stage 1.5F root contract / summary
  Section 6.3 consumer runtime attestation fields
```

这些字段不改变 formal revision JSONL row 或 Stage 1.5G 输入 schema；既有消费者必须忽略未知字段。producer manifest 与 consumer manifest 都以 policy version、sorted POSIX relative paths、UTF-8 和单个末尾 newline 计算 SHA-256，禁止依赖平台 path separator 或 JSON pretty-print。

---

## 7. Contract Impact Matrix

| Layer | Change | Compatibility Rule |
|---|---|---|
| `configs/base.py` | 保留 prerequisite config 名和值；默认值仍为空、producer 默认关闭 | `A -> B` 仅允许四个固定位置的 literal attestation assignment RHS delta；未提交改动、动态 RHS 或任何其他 config delta fail-closed |
| Stage 1.5D runner | 在现有 runner 内以 Git ancestry + protected tree/config delta + worktree/head/consumer checks 替代 SHA equality | Git/config/module path/worktree failure，或 ARMED 后 consumer failure latch 后返回 false；不终止 normal launch poll |
| Protected producer/consumer runtime code | 用固定清单限制 proof commit 之后的可变代码 | producer、1.5F revision lineage 或 1.5G lineage review 代码变化均需新的 proof commit；最终完全回退到 `A` 内容可通过 |
| Stage 1.5D runtime gate | 继续序列化既有 attestation 字段，并记录 policy/manifest hash/self output-root ID | 新字段仅供审计；既有消费者忽略未知字段 |
| revision producer/writer | 仅接收既有 `effective_enabled` | 不改变 formal row、JSONL schema 或 idempotency |
| Stage 1.5F | 不改变 JSONL 输入 schema；其 revision consumer 路径纳入 proof，并写出 startup/current runtime attestation 与 consumed Stage 1.5D root binding | enabled 1.5D 必须读取 fresh compatible 且绑定自身 output root 的 1.5F proof；producer 关闭时不增加 1.5F input 要求 |
| Stage 1.5G | 不改变 JSONL 输入 schema；其 lineage review 路径纳入 code-tree proof | offline reviewer 不成为 online producer gate |

---

## 8. Process Lifetime, Restart And Idempotency

Stage 1.5D attestation 不写入新的 state、JSONL 或 watermark。启动成功后仅在进程内保存 `startup_head_sha`、`producer_armed_once = false`、`runtime_attestation_compromised = false` 和尚未冻结的 consumer identity；它们不是 operator 输入，也不跨重启复用。1.5F 将自己的 startup/current consumer proof 写入既有 root contract 和 summary，以供 enabled Stage 1.5D 只读验证。

```text
DISABLED
  configured_enabled = false
  effective_enabled = false
  health = producer_disabled

BOOTSTRAP_WAITING_FOR_CONSUMER
  configured_enabled = true
  producer_armed_once = false
  effective_enabled = false
  health = prerequisites_unmet
  no consumer-missing latch

  E0 normal case: static/local proof is valid and only the 1.5F
  consumer candidate is not yet valid.
  Other unarmed prerequisite failures also remain fail-closed here;
  they require correction and restart, but never emit formal revisions.

ARMED
  all prerequisites are valid
  freeze expected_consumer_root_id and expected_consumer_process_instance_id
  producer_armed_once = true
  effective_enabled = true

COMPROMISED
  producer_armed_once = true
  AND any local or consumer runtime proof subsequently fails
  runtime_attestation_compromised = true
  effective_enabled = false
  restart required
```

部署 handshake 必须固定为三阶段：

```text
E0 Establish upstream
  start 1.5D at commit B with producer configured true but no consumer proof yet
  -> BOOTSTRAP_WAITING_FOR_CONSUMER
  -> normal launch collection and runtime gate remain READY

E1 Establish consumer
  start 1.5F at the same commit B with an events glob under E0's output root
  and the explicit E0 `live_safety_gate_summary.json` path
  -> wait for valid root contract and fresh consumer summary

E2 Arm producer
  restart 1.5D at the same commit B, same 1.5D output root,
  passing the explicit 1.5F root-contract and summary paths
  -> freeze consumer root/process identity
  -> ARMED only when every prerequisite passes
```

每个 poll 先执行 normal announcement/list/detail 和 normal launch handling；仅在 formal revision emission 之前执行总预算不超过 1 second 的 lightweight Stage 1.5D drift 与 1.5F consumer checks。启动 full proof 的预算为 10 seconds。local runtime failure 在任意生命周期均 latch；consumer failure 只有在 `producer_armed_once = true` 后才 latch。这样既避免“进程先加载代码、随后仓库切换到另一个 commit，却仍按新 `HEAD` 证明旧模块”，又避免 E0/E1 的启动循环死锁。不存在新的 JSONL crash window、migration 或 idempotency key。

---

## 9. Trusted Computing Base And Threat Boundary

### 9.1 Trusted Computing Base

本 design 明确信任以下基础：

1. local kernel、filesystem 和 OS process semantics 正常工作。
2. Git executable、Git object database 和 Python interpreter 未被恶意篡改。
3. 已安装第三方 Python packages 未被恶意修改。
4. local privileged/root operator 非恶意，且不会在 enabled process 运行时并发执行 `rsync`、Git mutation 或直接篡改 runtime artifact。
5. wall-clock 满足既有 runtime-gate freshness 假设。

### 9.2 Defended And Excluded Threats

本设计防止：错误/non-ancestor commit、受保护 producer/consumer tree 差异、config piggyback、dirty tracked source、rsync 产生的 uncommitted source、untracked/ignored Python shadow、错误 repository、shallow history、错误 module path、启动后 HEAD/worktree drift、stale/restarted/wrong 1.5F process、cross-root artifact mix-up，以及错误 revision transport capability。

本设计不防止：恶意 root 同时重写 Git/Python/runtime summary/process memory、被攻陷的 kernel/filesystem/Git/Python、第三方依赖供应链攻击或恶意时钟。若需要应对这些 host-level adversarial threat，必须另行建立 host/platform attestation design，不得继续扩大本 hotfix。

---

## 10. Evidence And Test Strategy

### 10.1 Required Tests

1. 真实临时 SHA-1 Git repo 创建 verified commit `A`，再创建仅修改 Section 4 四个固定 literal attestation RHS 的 enablement commit `B`；`A` 为 `B` ancestor、producer/consumer tree 等价、config AST delta 合法且 1.5F runtime proof fresh/compatible 时，在 `integration_health = ready` 下允许 effective enablement。
2. `A == B` 仍可通过；非祖先、未知 commit、空/短/非法 SHA、SHA-256 repository、非 Git directory、runner root 不匹配、commit-object 缺失或 manifest path 不是 blob 均 fail-closed。
3. `A -> B` 中 `False -> True`、或 prerequisite literal `"" -> proof commit A` 可以通过；`bool("false")`、`os.getenv(...)`、helper call、name/attribute/subscript expression、assignment 移位、duplicate、delete/add、`AnnAssign`、multi-target 或 compound assignment 均 fail-closed。
4. `A -> B` 夹带 lookback、Stage 1.5D threshold、anchor/runtime-gate config 或 `RISK_LIVE_TRADING_ENABLED = True` 时 fail-closed。仅四个 allowlisted literal attestation values 可以变化；任何其他 config AST delta 必须失败。
5. 任一 protected producer 或 consumer runtime path 在 `A` 与 `B` 最终内容不等时 fail-closed。若中间提交改动后 `B` 已完全恢复为 `A` 内容，则 tree-equivalence 可以通过。无关文档或测试变更不应造成失败。
6. 每个 manifest path 必须在 `A`/`B` 都存在且 tracked；故拼错、缺失或删除路径 fail-closed。静态 AST import-closure regression 必须覆盖所有 project-local runtime dependency，包括 relative import；任意 dynamic import construct、manifest 漏项或 critical module `__file__` 不在预期 repository path 的 shadow 情况 fail-closed。
7. protected runtime path 或 `configs/base.py` 有 unstaged/staged 修改时 fail-closed；四个明确 source dir 中存在普通 untracked 或 ignored `.py` 时 fail-closed；无关 `data/` 或 JSONL artifact 不应造成失败。
8. shallow repository 在 `merge-base` 前 fail-closed；测试断言不调用 network/deepen，且 Git command timeout/exception 或 poll aggregate budget 耗尽也 fail-closed。
9. 1.5F root contract/summary 缺失、stale、非 `v2_production`、consumer root ID 不等、root contract hash 不等、startup commit 不等于 1.5D startup commit、consumer manifest hash 不等、formal event/revision version `2` 任一未声明、consumer static/runtime attestation false、consumer latch true、admission block 或 blocker 非空时，Stage 1.5D producer 必须 fail-closed；fresh compatible consumer proof 才可通过。
10. 1.5F startup 必须拒绝 events-glob root 与 runtime-gate `source_root` 不同，或 runtime-gate file 不属于其 `source_root` 的情况；1.5D 必须拒绝健康但 `source_stage1_5d_output_root_id` 不等于自身 output root ID 的 consumer。E0/E1/E2 使用同一 1.5D root 时可通过；E2 重启 1.5D 但保持同一 output root 时，该上游 root binding 不得失效。
11. manifest hash 与 root-contract hash 必须分别验证：manifest 的 policy/path/newline canonicalization 跨平台稳定；root-contract hash 独立于 JSON key order/pretty-print，任一 root-contract attestation field 改变都改变 hash；summary 引用另一个 root contract 的 hash 必须被拒绝。root contract 不得含自指 hash 或可变 summary field。
12. 1.5F process restart 必须生成新的 process instance ID；1.5D arm 后 consumer root/process ID 的任何变化都必须 sticky compromise，即使 commit、manifest、upstream root 和 heartbeat 均仍有效。summary 必须使用 atomic replace；模拟半写/parse failure 必须 fail-closed。
13. 启动 static proof 失败后，即使 operator 在同一进程内校正 repository/config/worktree 也必须保持 disabled；Stage 1.5D 或 1.5F 在启动后出现 `HEAD B -> C -> B`、dirty 后 clean、untracked Python 删除、module-path mismatch 修复或 timeout 后成功，也均必须在同一进程保持 disabled；校正后重启才可重新验证。normal launch collection 继续。
14. E0 configured true 但 consumer paths 缺失/尚未 ready 时必须为 `BOOTSTRAP_WAITING_FOR_CONSUMER` 而非 compromised；E1 1.5F ready 后，E2 重启同 commit、同 Stage 1.5D output root 的 1.5D 才可首次 arm；ARMED 后 consumer failure 才 sticky。
15. `configured_enabled = false` 时，即使其他 prerequisite 全部成立，`effective_enabled = false`、health 为 `producer_disabled`；configured true 后 Git/config/worktree/module-path/consumer/Part A/fixture 任一不成立时 health 为 `prerequisites_unmet`；仅前提成立而 integration non-ready 时保持既有 integration health。
16. runner integration regression：prerequisite 不满足时 revision 只写 diagnostic，不写 formal revision；normal launch row 仍可写入。
17. runtime gate/root contract/summary regression：既有字段和值域兼容，新增 policy/manifest/process/source-root/consumer attestation 字段稳定且不改变 JSONL event schema。implementation-plan preflight 必须从 workspace 断言 current producer revision contract 为 v2、producer 只发 v2、1.5F production consumer 允许 `[1, 2]`，且 v1 仅走历史 compatibility path。

### 10.2 Fixture Provenance

Git attestation 测试使用 synthetic temporary Git history，仅证明 attestation 机制，不宣称真实交易所 revision evidence。

真实延期/改期/取消公告的冻结 BAPI payload 与 manifest 仍是未来 enablement 的独立必要条件；当前缺失该证据只阻止启用 producer，不阻止本修补的实现和部署。

---

## 11. Safety, Rollout And Rollback

### 11.1 Rollout

1. 部署 attestation 修补，保持所有 producer enablement 配置为 false。
2. 部署前确认 runner repository 为完整非 shallow Git worktree，且 protected runtime path 与 `configs/base.py` 均已提交；不接受 rsync 后的未提交运行代码作为 producer enablement 基础。
3. 验证 Stage 1.5D runtime gate 为 READY，`configured_enabled/effective_enabled = false`，正常 launch collection 可被 Stage 1.5F 消费。
4. 等待并冻结真实 revision evidence；完成 Part A、关联规则和人工复核。
5. 仅通过独立批准的后续 allowlisted-config commit 启用 producer；该 commit 以已经验证的 proof commit 为 prerequisite，不改动 protected producer/consumer runtime paths，且 config AST delta 仅涉及 Section 4 的四个 literal assignments。
6. 按 Section 8 的 E0/E1/E2 执行：E0 先启动 configured-true 的 1.5D 为 bootstrap waiting；E1 在同一 commit 启动 1.5F，并显式传入 E0 root 下的 `events/*.jsonl` 与 `live_safety_gate_summary.json`，验证 root contract/summary 的三个 source root ID 相等；E2 重启同一 1.5D root 并传入明确的 1.5F contract/summary paths 后首次 arm。不得以旧 1.5F 进程、跨 root input 或仅人工顺序代替 runtime gate。
7. enablement review 记录必须写明 `proof_commit_sha`、`part_a_suite_run_at_commit`、`fixture_reviewed_against_commit` 和独立 review verdict；`part_a_suite_run_at_commit` 必须等于 `proof_commit_sha`，fixture review 必须使用该 commit 的 parser/consumer 代码。这些记录是人工 evidence binding，不进入 runtime schema。

### 11.2 Rollback

若 Git attestation 出现异常或 runtime health 不符合预期：保持/恢复 `configured_enabled = false` 并重启 Stage 1.5D。不得通过跳过 attestation、伪造 SHA、dirty worktree 或直接设置 `effective_enabled` 进行绕过。

---

## 12. Historical Decision And Open Questions

本 design 明确 supersede 2026-08-04 Design Section 5.3 中的：

```text
prerequisite_commit_sha == running_commit_sha
```

新语义为本设计 Sections 6.3-6.4 的 ancestry、protected producer/consumer tree、config delta、worktree/module-path、live consumer process、同一 Stage 1.5D root binding 和 startup-head 组合证明。旧 design 保留为历史记录，不回写修改；implementation 完成后应在 roadmap/decision log 记录本次语义升级及其生效 commit。

当前 source-of-truth code 的 schedule revision producer contract 为 v2；v1 仅是历史 artifact compatibility，1.5F consumer 允许 `[1, 2]`。后续 implementation plan 的 preflight 必须从 workspace 再次验证这一事实，不能依赖 2026-08-03/2026-08-04 的历史文字。

无阻断实现路径的 Open Question。

真实 revision evidence 缺失仍是 future enablement blocker；Part A/fixture flag 仍须经独立人工复核，不能被此 Git attestation 自动证明。本次不改变 producer 默认关闭状态。
