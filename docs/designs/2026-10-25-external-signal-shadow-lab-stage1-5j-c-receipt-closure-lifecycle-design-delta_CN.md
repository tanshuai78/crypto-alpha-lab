# Stage 1.5J-C 收据闭环生命周期修复 Design Delta

**日期：** 2026-10-25

**状态：** `design_delta_candidate` / `hypothesis_only`；仅供独立 Design Review，未授权实施、重新验证、收据生成、commit、push、deployment、SSH 或任何 runtime action。

**父 Design：** [2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md](2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md)，SHA-256 `32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45`。

**适用批准 Plan：** [2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md](../plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md)，SHA-256 `827d1bbcabdd02f1d9d566752f1185e2e7aef49bb2a236660c8fc6a621d0ebe3`。该 Plan 的 Task 5/6 在本 Delta 经批准并由新的 Delta Plan 落实前，不能宣布完成。

## 1. 决策摘要

父 Design §9 要求独立审计报告写入 `.git/plan-execution/.../evidence/receipt_closure_audit_report.md`，但 `.agent/skills/audit-plan-completion/SKILL.md` 同时禁止 Completion Auditor 持久写入项目、evidence root 或 artifact。两条规则对同一必需动作给出了互斥的 owner，因此形成 `BLOCKED_SPEC_DRIFT`；这不是 executor 的局部实现缺陷。

本 Delta 采用一个最小的 **Evidence Recorder**：

1. 独立 Auditor 继续只读，并在其审计输出中给出一个确定的 canonical `AuditDecisionPayload` 字节序列。
2. 用户/Custodian 在取得该 payload 后，单独授权且 release 一次仅针对该 payload SHA、RUN_ID 和报告路径的 Recorder 写入。
3. Evidence Recorder 只能验证该 payload、第二授权链与既有 validation tuple 的绑定，再将 payload 所带的报告 UTF-8 字节原样写到既定 evidence 路径并生成 sidecar。
4. Recorder 不得执行 J-C CLI、domain replay、Rule 17 verifier、oracle、raw ZIP/CSV 读取、批准/authorization/release 创建，或自行判断审计结论。
5. 最终只读 Auditor 重新计算物理报告和 sidecar，确认其与其先前给出的 payload 完全一致后，才可接受 `receipt_closure_audited`。

这只修复终态审计的 writer ownership 与 Task 5 物理证据分层；不改变 J-C 的研究问题、60s/3s/15m 协议、任何 profile/schema、原始输入、现有 validation root、CLI source bundle 或权限集合。

## 2. 已确认事实、假设与非事实

### 2.1 已确认事实

1. 父 Design §9 第 384 行指定报告和唯一 `.md.sha256` sidecar 位于每个 RUN_ID 的 `evidence/` 子树；第 386 行把该审计结论作为闭环联合谓词的一部分。
2. `audit-plan-completion` 的 `Auditor Read-Only Invariant` 禁止 Auditor 持久修改任何项目文件、fixture、runtime evidence root 或 approved artifact；Auditor 只能在 isolated tempdir 进行临时负向探针。
3. J-C 的 producer 已独立写入 `producer_lifecycle_evidence.json`，其 owner 是 CLI；该文件证明 producer 成功发布，不是独立 closure verdict，不能改作 closure report。
4. 当前 J-C Rule 17 verifier 和 domain loader 不消费 `receipt_closure_audit_report.md`。本 Delta 不将报告纳入 receipt sealed tree、manifest、summary 或 profile `stage1_5j_c_time_path_v1`。
5. 已授权 validation 的 11-file source bundle 是 J-C CLI/core/verifier 与冻结上游文件的 identity；Recorder 不是 producer、loader 或 verifier，不能追溯性加入该 bundle。
6. Task 5 原有文字把 parser/package 与 lifecycle 两类负向证据混为一个“物理矩阵”。前者可以由 Task 2/4 的 isolated canonical/synthetic fixtures 证明；后者必须由 Task 5 对实际 production call order 或真实发布/authorisation 边界的隔离探针证明。

### 2.2 显式假设

1. 审计角色输出可以由用户原样转交给 Recorder；该转交不是对 Auditor 身份的密码学认证。该项目当前没有独立签名基础设施，本 Delta 不假装提供它。
2. Recorder 的进程执行仍须由后续 Plan 的受控实施者承担，但仅有 Delta Plan 的 implementation approval 不能替代一次性 `audit_recording_approval` / `audit_recording_release`。其输入、允许读取集、写入集和失败语义必须使其不能伪造或升级 Auditor verdict。
3. 已存在的 validation root 与 authority/evidence 文件保留原字节；若实施时其 source bundle、RUN_ID、triplet hash 或 authority tuple 不一致，按原 Design fail-closed，不以本 Delta rebaseline。

### 2.3 非事实与禁止推论

本 Delta 不证明任何 Alpha、经济收益、策略可执行性、外部审计身份、完整物理 probe 已通过，或 production diagnostic receipt 已生成。它也不赋予网络、signal、consumer promotion、paper trading、live trading、execution、commit、push、deployment 或 SSH 权限。

## 3. 考虑过的方案

| 方案 | 结论 | 理由 |
| --- | --- | --- |
| 让 Auditor 直接写报告 | 不采用 | 违反通用只读审计边界；会让每个审计成为可变更 workspace 的特殊例外。 |
| 让 Executor 写并自称独立闭环 | 不采用 | producer/executor 不能拥有独立 verdict 的写入权，破坏职责分离。 |
| 报告仅留在仓库外 | 不采用 | 当前 J-C lifecycle 已把 RUN_ID evidence tree 作为可复核证据位置；完全外置会降低重审可验证性。 |
| **Auditor 只读 payload + 最小 Evidence Recorder** | **采用** | 保留职责分离、保留项目内可复核报告，并把唯一写能力缩减到确定字节的记录动作。 |

## 4. 范围与显式非目标

### 4.1 范围

1. 用本 Delta 的契约替换父 Design §9 中“独立审计员写报告”的 owner 语义，保留原报告路径与内容下限。
2. 增加 stage-specific Recorder、其最小测试、独立 payload/recording contract 和一次性 Recorder evidence-write authorization。
3. 将 Task 5 的负向证据区分为 test-level input/parser proof 与 physical lifecycle proof，并明确最小物理矩阵。
4. 为已存在、未被覆盖的 validation RUN_ID 提供一次 recorder-only completion path；不重跑 CLI、不覆盖三件套、不新建诊断 root。

### 4.2 非目标

- 不变更 `stage1_5j_c_time_path_v1` profile ID/version、manifest/summary/review schema、J-C domain loader 或 Rule 17 verifier的 acceptance grammar。
- 不变更 J-A/J-B code、verifier、receipt、closure evidence、ledger、protocol、配置、风险阈值或 parent Design 本体。
- 不构建通用审计框架、签名系统、角色管理、队列、数据库或长期服务。
- 不将 unit test 伪装成 raw-to-output positive proof，也不以 Delta 降低 CLI/domain replay/verifier/oracle 的既有正向门槛。

## 5. 更新后的角色与允许能力

| 角色 | 可读取 | 可写入 | 明确禁止 |
| --- | --- | --- | --- |
| Custodian | 用户批准原文、Plan/Design/source/input seals、Auditor payload SHA | validation approval/release 及其 sidecar；以及本 Delta 唯一的 recording approval/release 及其 sidecar | CLI、raw、receipt、AuditDecisionPayload、closure report verdict |
| Executor / Producer | 原 Design 授权的 source/input 和 validation root | 仅原 Design 指定的 triplet、derived authorization、producer lifecycle evidence | closure report、AuditDecisionPayload、独立 verdict |
| Independent Auditor | workspace、authority、validation root、raw 的只读路径；isolated tempdir | 仅 isolated tempdir | 项目、`.git/plan-execution`、validation root 和任何 persistent evidence 写入 |
| **Evidence Recorder** | payload、validation authority tuple、recording approval/release、validation root 三件套、producer lifecycle evidence | 仅既定 `evidence/receipt_closure_audit_report.md` 与唯一 sidecar | raw ZIP/CSV、J-C core/CLI/domain loader/verifier/oracle 调用、approval/release/run authorization、triplet、lifecycle evidence、任何 verdict 计算或权限变化 |

Recorder 不属于 TCB 中的 producer/verifier。其脚本 exact SHA 必须被 `AuditDecisionPayload` 和最终审计记录绑定，但不得加入既有 11-file source bundle，避免无关 recording code 反向使历史 canonical validation 无效。

## 6. `AuditDecisionPayload`、第二授权链与 Recorder 状态机

### 6.1 两条不可互换的 authority chain

本 Delta 明确区分 validation 与 recording。旧 validation chain 只授权 J-C 读取 frozen inputs 并向 validation root 产生 `validation_only` 三件套；它永不授权新增 writer。Recorder chain 只授权对已经存在的同一 validation RUN_ID 记录一个固定 Auditor payload；它不授权 CLI、receipt regeneration 或输入消费。

| 链 | 必须绑定的身份 | 允许动作 |
| --- | --- | --- |
| validation | `validation_design`、`validation_plan`、`validation_user_receipt_generation_approval`、`validation_authorization_release`、`validation_run_authorization`、11-file source bundle、input seals、RUN_ID/root/triplet | 已完成的 J-C `validation_only` 生产、只读 replay/verifier/audit |
| recording | `recorder_delta_design`、`recorder_implementation_plan`、`user_audit_recording_approval`、`audit_recording_release`、payload SHA、Recorder source seal、同一 RUN_ID/root/report path | 一次 Recorder report/sidecar 写入和随后只读复核 |

`user_audit_recording_approval.txt` 是唯一的用户 evidence-write 授权，必须是 ASCII、精确 15 行、末尾一个 LF，且按下列顺序无重复键：

```text
operation=record_stage1_5j_c_receipt_closure_audit_once
run_id=<existing validation RUN_ID>
validation_receipt_root_absolute_path=<existing absolute validation root>
report_relative_path=evidence/receipt_closure_audit_report.md
audit_decision_payload_sha256=<payload SHA-256>
validation_design_relative_path=<parent Design path>
validation_design_sha256=<parent Design SHA-256>
validation_plan_relative_path=<approved R1 Plan path>
validation_plan_sha256=<approved R1 Plan SHA-256>
recorder_delta_design_relative_path=<this Delta path>
recorder_delta_design_sha256=<this Delta SHA-256>
recorder_implementation_plan_relative_path=<approved Delta Plan path>
recorder_implementation_plan_sha256=<approved Delta Plan SHA-256>
recorder_relative_path=scripts/governance/record_stage1_5j_c_receipt_closure_audit.py
recorder_source_sha256=<Recorder source SHA-256>
```

Custodian 仅在逐字核对该用户原文、payload SHA、两条 chain 的 physical seals 后，写入同一 authority RUN_ID directory 的 `audit_recording_release.json` 及唯一 `.sha256` sidecar。release canonical JSON 的 exact keys 为：`alpha_claim_allowed,audit_decision_payload_sha256,consumer_promotion_allowed,execution_allowed,live_trading_allowed,network_allowed,paper_trading_allowed,receipt_regeneration_allowed,recorder:FileSeal,recorder_delta_design:FileSeal,recorder_implementation_plan:FileSeal,release_schema_version,release_state,report_relative_path,run_id,signal_allowed,user_audit_recording_approval:FileSeal,validation_receipt_root_absolute_path,validation_design:FileSeal,validation_plan:FileSeal`；version 只能为 `1`，state 只能为 `user_message_verified_and_released`，八项 `*_allowed` 必须都是 literal JSON `false`。该 release 不包含且不得改变 validation approval/release/run authorization。两份 recording 文件都不属于 J-C receipt sealed tree、11-file source bundle 或 existing evidence directory。

### 6.2 `AuditDecisionPayload` 传递、结构与 verdict projection

Auditor 在只读审计回复中输出一个单独、完整、UTF-8 canonical JSON（sorted keys、`,`/`:` separators、一个 LF、无 BOM）的 `AuditDecisionPayload`。用户只能原样将该字节序列放入仓库外的临时 handoff regular file；Recorder 不将 payload 文件作为长期 artifact 保存，也不接受任何 payload override 参数。

Payload exact top-level keys：

```text
artifact_kind: str
audit_payload_schema_version: int
manifest_sha256: str
receipt_root_absolute_path: str
recorder_delta_design: FileSeal
recorder_implementation_plan: FileSeal
recorder_relative_path: str
recorder_source_sha256: str
report_relative_path: str
report_sha256: str
report_utf8: str
review_sha256: str
run_id: str
summary_sha256: str
validation_authorization_release: FileSeal
validation_design: FileSeal
validation_plan: FileSeal
validation_run_authorization: FileSeal
validation_user_receipt_generation_approval: FileSeal
verdict: str
verifier_relative_path: str
verifier_source_sha256: str
```

`audit_payload_schema_version` 必须为 JSON integer `1`；`artifact_kind` 必须严格为 `validation_only`；`verdict` 只能为 `receipt_closure_audited` 或 `receipt_closure_incomplete`；所有 SHA 为 64 位小写十六进制；所有 `FileSeal` 均为 exact `{relative_path,size_bytes,sha256}`。Payload 中的两条 Design/Plan tuple 必须分别与其对应 authority chain 相符，禁止将旧 R1 Plan 冒充 Recorder Plan，或以 Recorder Plan 替换 validation Plan。

`report_relative_path` 必须严格等于 `evidence/receipt_closure_audit_report.md`。`report_utf8` 编码后的 SHA-256 必须等于 `report_sha256`，且不得为空；正文第一行必须精确为 `closure_verdict=<payload verdict><LF>`，且报告中仅允许这一行以 `closure_verdict=` 开头。Recorder 必须拒绝该 projection 不成立的 payload。报告仍必须保留父 Design §9 所要求的 authority、source/verifier、profile、artifact kind、RUN_ID、triplet SHA、actual RC、oracle、negative probe、scope/index/no-touch 内容。

### 6.3 Recorder 的输入、排他锁与持久化状态机

Recorder 必须是单一 stage-specific stdlib script：

```text
scripts/governance/record_stage1_5j_c_receipt_closure_audit.py
```

它只接受一个 payload 文件路径。不得接受 project-root、RUN_ID、output root、profile、权限、Plan 或结果覆盖参数。它必须验证 payload 的 regular-file/no-symlink、UTF-8、canonical JSON、exact key set、primitive type、enum、path、verdict projection 和 hash grammar；然后逐字段比较 validation chain、recording chain、payload、physical validation root、triplet 和 producer lifecycle evidence。若 payload 的 recorder path/SHA 不等于自身固定 identity，必须 `STOP=stage1_5j_c_audit_recording_payload_mismatch`。

在读取或变更任何 Recorder-owned staging/final file 前，Recorder 必须对 evidence directory 的 file descriptor 使用 non-blocking `fcntl.flock(LOCK_EX|LOCK_NB)`。这个 directory-FD lock 不创建持久 lock file；不支持、打开失败或已被占用均为 `STOP=stage1_5j_c_audit_recording_lock_unavailable`。持锁期间，Recorder 不得使用 `os.replace`，而是只可用同目录 staged regular file 的 `os.link(staging, final)` 发布；`FileExistsError` 是 STOP，确保并发 writer 不能替换 final inode。

在锁内以 `lstat` 验证 authority tree 到 evidence directory 的祖先无 symlink，且重新哈希 validation root 的 `manifest.json`、`summary.json`、`review_CN.md`，与 payload 及 `producer_lifecycle_evidence.json` 的物理 tuple 一致。Recorder 不得调用 loader、verifier、oracle 或读取 raw package。

`L` 表示已验证的 lifecycle 两件套，`R` 表示报告，`S` 表示报告 sidecar，`T_R` 表示 `.receipt_closure_audit_report.<payload-sha256>.staging`，`T_S` 表示 `.receipt_closure_audit_report.sha256.<payload-sha256>.staging`。`T_R` 内容必须是 payload 的 report bytes，`T_S` 内容必须是精确 sidecar bytes；任一调用最多只能遗留一个 staging。目录中任一其他文件或目录都是异常。锁内状态矩阵如下：

| 状态 | 精确目录成员 | 唯一允许行为 |
| --- | --- | --- |
| `S0` | `L` | 写入并 fsync `T_R`；`os.link` 发布 `R`；fsync evidence directory；unlink `T_R` 并 fsync；写入、fsync、link、fsync、unlink、fsync `T_S`/`S`。 |
| `S1` | `L + R`，且 `R` hash 等于 payload | 先 fsync evidence directory 重新确认 `R` 的持久化边界，再只发布 `S` 并 fsync directory。 |
| `S2` | `L + R + S`，三者 grammar/hash 全匹配 | 再次 fsync evidence directory 后幂等 `RC=0`；不得重写任何 final inode 或 mtime。 |
| `S3` | sidecar-only、任一 hash/symlink/成员异常、多个 staging 或未知成员 | `STOP=stage1_5j_c_audit_recording_target_exists_mismatch`，不得覆盖或删除 final。 |
| `S4` | `S0 + T_R`、`S1 + T_R`、`S1 + T_S` 或 `S2 + T_S` | 仅当 staging 为 regular non-symlink、名称和对应 report/sidecar bytes 都精确时，unlink staging 并 fsync directory 后重新分类；否则 STOP。 |

`R` 与 `S` 都须先写到对应同目录 staging、`fsync` staging file 后以 `os.link` 发布；每次 link/unlink 后都须 `fsync` evidence directory。directory fsync 失败即 `STOP=stage1_5j_c_audit_recording_persistence_failure`；下次调用必须按 `S0` 至 `S4` 重新验证，不能仅因文件可见而成功。成功只可返回 `RC=0`；任一失败不得产生不同报告字节、改变 verdict 或触碰 receipt/root/authority 的其他文件。

### 6.4 最终只读复核

新的或同一独立 Auditor 后续复核时，必须重新计算 report SHA、sidecar grammar、payload-to-report byte identity、validation chain、recording chain、payload SHA、Recorder source SHA、state-matrix final membership和 payload verdict projection；还必须确认 Recorder 未被用于任何 raw/domain/verifier execution。只有该复核和父 Design §9 的其余联合谓词都通过，`receipt_closure_audited` 才是可接受 closure 状态。

## 7. Task 5 负向证据分层

### 7.1 不变的 test-level 证据

下列属于 parser/reducer/serializer 或 isolated fixture 行为，继续由 Task 1-4 测试证明：package identity、CHECKSUM、ZIP/CSV/header/line/ratio/read cap、path/symlink containment、Decimal/time/order、gap/null、first passage、structural schema、独立 fixture oracle 和 renderer。它们不得被删除或以 Recorder 测试替代。

此外必须保留一项 `P-AD-01` production-admission integration negative proof：测试先通过 J-A canonical strict loader 在隔离物理 root 中取得实际 `archive_package_records`，随后只变异一个已准入 package、CHECKSUM 或 package identity 字节，再通过 producer 实际调用的 J-C admission/reducer entry path 读取该对象。它必须由 J-C package admission owner fail-closed，不得用 J-C helper mock、手工 package record 或宽松 fake loader 替代。该测试可以属于 Task 2/4，不要求重跑完整 Task 5 canonical validation；其目的仅是证明真实 J-C consumer call chain 不会绕开 package admission。

### 7.2 必需 physical lifecycle matrix

Task 5 仍必须实际运行一次 canonical positive validation，但物理负向 probe 收敛为以下六项。每项必须在 isolated temp copy 或 disposable authority/output root 中执行，记录实际 command、RC、expected owner 与 no-write proof；不得变异 JA/JB seals、正式 receipt 或唯一 canonical validation root。

| ID | 变异/故障 | 必须失败的 owner |
| --- | --- | --- |
| `P-LC-01` | locally self-consistent approval/sidecar/derived authorization 缺 Custodian release | CLI preflight，在任何 upstream loader 前停止 |
| `P-LC-02` | external release/derived authorization 的 `output_root` 与 receipt root 不一致 | CLI preflight；若在发布后引入，Auditor tuple comparison 也必须失败 |
| `P-LC-03` | sealed receipt 的 root/path/symlink 或 extra/missing artifact | standalone Rule 17 verifier |
| `P-LC-04` | raw 与 receipt 自洽但 child/Parent/group/prose 语义被伪造 | J-C domain replay / independent oracle |
| `P-LC-05` | parent-directory fsync after rename fault | producer 非零且 lifecycle evidence 缺失；closure predicate 必须为 false |
| `P-LC-06` | 第二 recording approval/release 与 payload SHA/Delta Plan/Recorder SHA 任一不一致；S0-S4 的 report/sidecar crash recovery、directory fsync failure、并发锁或 final inode collision | Evidence Recorder 以对应 STOP 停止，或仅按匹配 state matrix 恢复，绝不覆盖 |

本表取代父 Design §9/原 Plan Task 5 中将 `source/package/checksum/path/symlink` 全部再次要求为 physical lifecycle mutation 的宽泛表述；其中 package/checksum parser 证明仍是必需测试证据，且 `P-AD-01` 保留 production-admission integration negative proof。任何删减、替换或新增 physical probe 需新的 Design Delta，不能由 executor 自行解释。

## 8. 更新后的不变量与失败语义

| ID | 不变量 |
| --- | --- |
| `INV-13` | Auditor 永远只读；持久 closure report 只能由 Recorder 根据 Auditor 产生的 exact payload 原样写入。 |
| `INV-14` | Recorder 不拥有 source/raw/parser/reducer/verifier/oracle/authorization/receipt writer/verdict authority；其可写集合精确为单个 report 和 sidecar，且须先持有 evidence-directory 排他锁。 |
| `INV-15` | validation chain 与 recording chain 分别精确绑定；payload、两条 authority、validation root、triplet、Recorder source、payload SHA 与报告字节任一不一致都不产生 `receipt_closure_audited`。 |
| `INV-16` | S0-S4 状态机、non-overwrite publication、directory fsync 与恢复语义完整覆盖首次、部分发布、重复、并发与崩溃；文件可见不等于记录成功。 |
| `INV-17` | 物理 lifecycle matrix、`P-AD-01` production-admission integration proof 与 test-level parser matrix 分层且各自不可替代；green unit tests 不能代替 P-LC-01 至 P-LC-06。 |

新增 STOP 语义至少包括：

```text
STOP=stage1_5j_c_audit_recording_payload_mismatch
STOP=stage1_5j_c_audit_recording_authority_mismatch
STOP=stage1_5j_c_audit_recording_triplet_mismatch
STOP=stage1_5j_c_audit_recording_target_exists_mismatch
STOP=stage1_5j_c_audit_recording_symlink_or_escape
STOP=stage1_5j_c_audit_recording_lock_unavailable
STOP=stage1_5j_c_audit_recording_persistence_failure
```

任一 STOP 的唯一允许结论是 `receipt_closure_incomplete` 或 Plan-level `BLOCKED_IMPLEMENTATION_DEFECT` / `BLOCKED_SPEC_DRIFT`，由失败归属决定；不得生成替代报告、覆盖 evidence、换 RUN_ID、重新运行 canonical CLI，或将 Recorder green 等同于 domain replay/verifier green。

## 9. 契约影响矩阵、兼容性与恢复

| 组件 | 改动 | 兼容性规则 |
| --- | --- | --- |
| J-C receipt/profile/verifier/domain loader | 无 | profile ID/version、sealed tree 和 acceptance bytes 不变。 |
| Existing validation root | 无 | 不重跑、不覆盖 triplet；仅在父 Design 已预留 evidence directory 中追加报告及 sidecar。 |
| Existing authority RUN_ID directory | 增加四个 recording-authority files | 只允许 Custodian 在 payload 已输出后创建 `user_audit_recording_approval.txt`、其 sidecar、`audit_recording_release.json`、其 sidecar；不修改既有 validation authority files。 |
| Producer lifecycle evidence | 无 | Recorder 只能读/比较，不能创建、修改或补写。 |
| Auditor | owner 由“写报告”改为“输出 payload” | 仍完全遵守只读 skill。 |
| Evidence Recorder | 新增单用途 writer | 不可复用为通用 framework；只针对 J-C 和本 payload version。 |
| Completion audit | 增加 payload-to-report byte identity 检查 | 仍必须运行独立 verifier、domain replay 和所有既有 safety/scope gates。 |

现有 validation run 若其 11-file source bundle、approved parent Design/Plan、protocol、input seals、validation authority tuple和三件套 SHA 都未改变，可在 Delta Plan 的 recorder-only path 中保留为原始 positive evidence。若 J-C core/CLI/verifier/protocol、任一 frozen input，或 validation root/authority tuple 已变，旧 validation 必须按父 Design 失效，且需要新的独立授权/RUN_ID；Recorder 自身代码变化不改变这一判断，但其自身 SHA、Delta Plan identity 和一次性 recording approval/release 必须被 payload 与最终审计分别绑定。

## 10. L0/L1/L2 边界与验证策略

所有权限保持 false：`network_allowed`、`signal_allowed`、`paper_trading_allowed`、`live_trading_allowed`、`execution_allowed`、`alpha_claim_allowed`、`consumer_promotion_allowed` 和 `receipt_regeneration_allowed` 均不变。Recorder 不读取网络、不使用 API key、不触发 collector、订单、仓位、VPS 或 deployment。

本 Delta 的 L2 项为 `N/A`：它不改变研究样本、观察规则、结果 reducer、成本假设或任何 claim level；只修复既有历史诊断证据的治理生命周期。原 J-C 的 `hypothesis_only` 与 `validation_only` 语义不升级。

后续 Delta Plan 至少必须包含：

1. Task 0：重算父 Design、Delta、Plan、validation source bundle、authority/root/triplet 和 Git/no-touch inventory；若已有 J-C bytes 变化，立即停止而非复用验证。
2. Recorder RED/GREEN 测试：canonical payload、两条 authority chain、每个 `INV-13` 至 `INV-17` 变异、S0-S4、existing report/sidecar idempotency、partial publication/recovery、directory fsync failure、directory-FD lock contention、non-overwrite publication、symlink escape 和禁止 raw/producer/verifier imports。
3. `P-AD-01` 与物理 `P-LC-01` 至 `P-LC-06` actual RC matrix，全部使用 disposable copies/roots。
4. 一次只读 Auditor payload 生成、一次用户/Custodian recording authorization/release、一次受控 Recorder invocation、再一次独立只读 Auditor payload-to-report closure review。
5. `scripts/governance/verify_artifact_schema.py` 仅继续验证适用的 J-A root；J-C 使用其 standalone verifier，因为 J-C validation root 是绝对临时路径且不属于通用 verifier 的 project-relative profile。最终报告必须记录这一区分、J-A profile/verifier SHA/artifact hashes，以及 J-C verifier SHA/triplet hashes。

## 11. Open Questions 与交付边界

| Open Question | 阻断性 | Owner / 决策 |
| --- | --- | --- |
| Auditor payload 的外部传递没有密码学签名 | 不阻断 | 用户原样转交；当前项目未批准签名/identity infrastructure。任何要求强身份认证需独立治理 Design。 |
| 已有 validation RUN 是否保留 recorder-only closure eligibility | 不阻断，但 Task 0 必须验证 | Delta Plan 仅在原 source/input/authority/triplet bytes 全部一致时允许；否则不复用。 |
| 原 Plan 的完整 physical matrix 是否已有部分可复核证据 | 不阻断本 Delta | Delta Plan 按 `P-LC-01` 至 `P-LC-06` fresh evidence 重建，不以 executor summary 自动继承。 |

本 Delta 的交付是经过独立审查和用户批准的 Design Delta。批准本 Delta 不授权 Recorder 实现、payload 生成、closure report 写入、重新运行 raw validation，或任何其他 runtime action；后续必须先有单独绑定本 Delta 的 Implementation Plan 和用户实施批准。
