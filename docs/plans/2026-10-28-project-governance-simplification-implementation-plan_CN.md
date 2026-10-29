# 项目治理精简与规则归属 Implementation Plan

> 执行者：仅在本 Plan 经 B 审核、用户明确批准后使用 `executing-plans`；项目 workflow 覆盖上游默认 worktree、逐 Task commit 和自动执行选项。本轮只起草，不实施。

日期：2026-10-28。修订：2026-10-29。状态：`candidate / pending_closure_confirmation`。

**Goal：** 将工程规则集中到 L1，按实际影响选择流程和验证，迁移重复入口，并在独立验收和用户接受之前隔离候选治理。

**Architecture：** 原位维护窗口；AGENTS 为入口、L1 为工程规则正文、workflow 为阶段编排、项目 skill 为审查方法、Prompt 为角色调用。保留 L0/L2、第三方技能和历史批准对象。

**Tech Stack：** Markdown、Git、`rg`、`shasum` 和现有只读检查工具；不新增 Python、依赖、服务或自动授权机制。

## 1. Authority Binding

| 对象 | 绑定 |
|---|---|
| 已批准 Design | `docs/designs/2026-10-27-project-governance-simplification-design_CN.md` |
| Design SHA-256 | `6e95875502320ede179d8d01b045aaf1ef4d86103748dcded09704a6bd527094` |
| 用户批准 | 本会话明确批准上述路径/SHA，并仅授权起草 Implementation Plan |
| B review | 用户转交 `RECOMMEND_APPROVE`，上一轮 2 P0、2 P1 均关闭；不将 B 建议视为用户实施授权 |
| Planning HEAD | `71a44ff3c4e256e989fc7dd37fb4ac307bbb7f04`，仅为起草事实，不代替 Task 0 执行基线 |
| Planning worktree | 起草前仅上述 Design 未跟踪；tracked/index 无变更 |

Design 内的 candidate 状态文字属于已批准 bytes，不为更新状态而改写。批准事实来自用户消息与实际 SHA。执行时另核对本 Plan 的用户批准 path/SHA，不在 Plan 内嵌自身哈希。

本计划属于治理文档变更，不产生 Alpha、PnL 或交易可行性结论。L2 内容保持不变；研究专用要求不能被通用模板精简覆盖。Design §8 的迁移规则是本次明确批准的特殊要求，不允许执行者提前使用未来简短流程自批。

## 2. Allowed Change Scope

Allowed implementation paths: `none`（无业务或治理程序代码修改）。

Allowed verification paths: `none`（无测试代码新增；仅修改下表既有 Markdown 场景）。

Allowed documentation paths：下表 ID 是本文任务引用的精确路径，不是额外注册表。

| ID | 路径 | 操作与边界 |
|---|---|---|
| D01 | `AGENTS.md` | 修改入口、规则引用、三个参数镜像及任务路由；保留独立安全约束 |
| D02 | `.agent/rules/L1_Engineering_Process.md` | 工程规则唯一完整正文及旧编号别名 |
| D03 | `.agent/rules/ponytail.md` | 项目适配精简，不修改上游技能 |
| D04 | `.agent/workflows/design-contract.md` | 按影响展开的 Design 流程 |
| D05 | `.agent/workflows/implementation-plan.md` | 按影响展开的 Plan 流程 |
| D06 | `.agent/workflows/execute-approved-plan.md` | 受控实施、证据及检查适用范围 |
| D07 | `.agent/workflows/remediate-completion-audit.md` | 实现修复、有限 Plan 增补、Design 变化分流 |
| D08 | `.agent/skills/reviewing-implementation-plans/SKILL.md` | Plan 审查方法 |
| D09 | `.agent/skills/reviewing-implementation-plans/README.md` | 入口与适用范围同步 |
| D10 | `.agent/skills/reviewing-implementation-plans/REVIEW_CHECKLIST.md` | 删除重复规范和无条件全量检查 |
| D11 | `.agent/skills/reviewing-implementation-plans/PRESSURE_TESTS.md` | 对应 Design 场景及保留必要历史案例 |
| D12 | `.agent/skills/audit-plan-completion/SKILL.md` | 独立只读审计方法 |
| D13 | `.agent/skills/audit-plan-completion/PRESSURE_TESTS.md` | 完成、范围、身份及权限场景 |
| D14 | `.agent/skills/closure-revision/SKILL.md` | Design/Plan 有界返修方法 |
| D15 | `.agent/skills/closure-revision/INSTALL.md` | 删除整目录覆盖和复制完整规则的安装指引 |
| D16 | `.agent/skills/closure-revision/references/design-plan-checklists.md` | 仅适用时读取的详细检查 |
| D17 | `.agent/skills/closure-revision/references/revision-control-packet.md` | 可选记录模板，不强制独立产物 |
| D18 | `.agent/skills/closure-revision/references/revision-failure-patterns.md` | 反例与新边界一致 |
| D19 | `docs/production_artifacts/tri_agent_prompt_library_CN.md` | 所有角色及严格模式附录同步 |
| D20 | `.agent/skills-sources.md` | 新建简短来源说明，不参与批准或 runtime |
| D21 | `.agent/workflows/bugfix.md` | 迁移现行入口后删除 |
| D22 | `.agent/workflows/feature.md` | 同上 |
| D23 | `.agent/workflows/refactor.md` | 同上 |
| D24 | `AGENTS_CN.md` | **范围增补请求**：只在开头增加旧版译本说明与当前权威入口，不重译、不删正文 |

**D24 的显式增补依据：** Design §8 允许发现名单外有效引用时申请有限范围增补。实际检索发现 `AGENTS_CN.md:136-145` 引用三个待删除文件，且首页将其描述为长期规则。该文件受 Git 跟踪，不能当作不存在或擅自覆盖。本 Plan 请求将 D24 一并交 B 审核及用户实施批准；未获包含 D24 的批准时，不执行 D24、删除任务或最终切换，不宣称全 Plan 完成。不是追加业务范围，也不修改已批准 Design。

Allowed generated/runtime artifacts：仅执行基线目录，不是研究 receipt 或机器授权输入。

```text
$(git rev-parse --git-path plan-execution/governance_simplification)/<UTC>.<mktemp-suffix>/
  base-sha.txt
  status.txt
  worktree.patch
  index.patch
  untracked-paths.txt
  untracked-sha256.txt
  old-authority-paths.txt
  old-authority.sha256
  old-authority/<原相对路径>
  references-before.txt
  execution-notes.md
  candidate-sha256.txt
```

`old-authority` 的来源限于 AGENTS、AGENTS_CN、`.agent/rules/`、`.agent/workflows/`、`.agent/skills/` 内现有受 Git 跟踪文件、D19，以及本次已批准 Design/Plan；另外纳入上述治理来源路径内经 Task 0 确认实际适用的未跟踪文件，不能以未纳入 Git 为由遗漏。只保存执行前 bytes，不全量备份无关 untracked 文件。发现实际适用来源位于该范围外时，停止相关迁移并请求有限来源范围增补，不静默遗漏或扩大备份范围。其用途为人工回读与版本比对，不新增 schema、sidecar、Custodian、Recorder 或自动准入程序。来源识别和副本保存不授予修改源文件的权限，D01-D24 修改白名单不变；不得创建其他 `.git` 权威文件、修改 index 或 Git 配置。

Affected but unchanged：

| 文件/对象 | 保持兼容的依据与检查 |
|---|---|
| `.agent/rules/L0_Financial_Safety.md`、`.agent/rules/L2_Alpha_Research_Methodology.md`、`configs/base.py` | 前后身份不变；D01 的资金约束和 L2 路由仍保留，三参数只改说明引用 |
| 第三方 `.agent/skills/` 文件及其 reviewer prompts | 原 bytes 不变；适配在 D04-D07 调用前明确提供，不在上游文件里打补丁 |
| `.agent/tools/anti_shortcut_scan.py`、`scripts/governance/verify_artifact_schema.py` | 不改工具；检查引用范围，不变更既有 profile 的准入行为 |
| `docs/ops/2026-08-07-project-development-workflow-manual_CN.md` | 已核对其适用范围为非平凡工作，主链入口四个路径保留；D01/D19 明确新任务以现行 L1/workflow 为准，旧操作说明不能成为追加审批权或简短任务门禁 |
| 历史 Design/Plan、J-A/J-B/J-C source/profile/receipt | 不改 bytes，不将其完成义务迁移到新 Rule 17；通过 diff/scope 与 S9/S15/S16 核对，不重跑 raw |
| `graphify-out/` | 查询仅提供线索，不运行 update，不改图谱 |

Forbidden：除上述清单外的一切修改；尤其是 L0/L2、configs、src、scripts、tests、data、历史文档、已批准 Design/Plan、第三方/全局技能；禁止安装更新、网络、SSH、部署、runtime、paper/live、commit/push、自动暂存、全库 autofix、破坏性 reset/clean。Plan 起草不创建执行基线目录。

## 3. 影响核查与实施顺序

已读取当前规则、workflow、三个项目技能及其附属入口、Prompt；`graphify query` 和 `graphify path` 均 RC=0，但图谱结果存在截断且可能过时，只作线索。实际 `rg --hidden` 在排除 `.git/.venv/data/graphify-out` 和历史 Design/Plan 后，发现待删除 workflow 的引用者是 D01、D24。不能据此保证未来执行时无新增引用，Task 0 必须重查。

阶段职责顺序：`Task 0 → Task 1 → Task 2 → Task 3 → Task 4 → Task 5`。全部在同一维护窗口完成，不按 Task 激活部分规则。执行者按下面步骤做文档差分和场景走查，不为文字改动制造业务 TDD 或模拟市场数据。

## 4. Task 0：批准核对、保存基线、维护窗口

**映射：** INV-01/02/06/07/08，S9/S10/S13/S18。**修改：** 仅声明的 baseline 目录；规则文件尚不写。

1. 校验 Design SHA、本 Plan 用户批准 SHA、B verdict 与 D24 增补范围。任何不一致停止 `approved_authority_mismatch`。记录当前 `BASE_SHA`、index/worktree/untracked；Planning HEAD 不能代替执行值。
2. 用户确认同一工作区其他开发/审计会话已经暂停。该确认与 Plan 批准可以在同一用户消息中给出，但不能推定“批准 Plan”等于已经停止其他会话。未确认则停在 `maintenance_window_unconfirmed`；不操作 VPS 或其他项目。
3. 用原生工具创建新目录，碰撞不覆盖。依现行执行 workflow 保存 status、二进制 patch、untracked 路径/哈希。记录准确路径，并保存所列旧权威文件的可读副本和 SHA；复制失败或核对不一致时，不得开始修改规则。

```bash
BASE_SHA=$(git rev-parse HEAD) &&
BASE_PARENT=$(git rev-parse --git-path plan-execution/governance_simplification) &&
mkdir -p "$BASE_PARENT" &&
E=$(mktemp -d "$BASE_PARENT/$(date -u +%Y%m%dT%H%M%SZ).XXXXXX") &&
printf '%s\n' "$BASE_SHA" > "$E/base-sha.txt" &&
git status --short --untracked-files=all > "$E/status.txt" &&
git diff --binary > "$E/worktree.patch" &&
git diff --cached --binary > "$E/index.patch" &&
git ls-files --others --exclude-standard > "$E/untracked-paths.txt"
```

4. 用 `git ls-files` 枚举第 2 节固定的 tracked 来源并显式加入已批准 Design/Plan；同时读取 `git ls-files --others --exclude-standard` 的实际结果，检查未跟踪文件是否位于治理规则、workflow、项目技能或 Prompt 的实际生效路径。结合 AGENTS/workflow/skill/Prompt 的引用和可核验的客户端加载依据分类，不能把“未跟踪”或“文本检索未命中”直接解释为不生效。在现有 `execution-notes.md` 中记录相关文件的路径、SHA、归属、分类（确认适用/确认无关/待确认）及可回读的加载或引用依据，不另建台账文件。

确认适用且在第 2 节来源范围内的未跟踪文件，与 tracked 来源合并去重后列入 `old-authority-paths.txt`；按原相对路径复制原始 bytes 到 `old-authority/`，逐文件用 `cmp` 和 `shasum -a 256` 核对，保存 `old-authority.sha256`，校验应 RC=0。原始内容和分类依据必须均可供独立审计回读；不能只留路径/hash 或执行者“已加载”的断言。dirty 文件同样复制当前 bytes，不把既有改动归属本任务。普通无关 untracked 文件只按原流程保留路径、SHA 和归属，不进入旧权威集合；相关但作用无法判断、依据不可回读或原 bytes 无法保存时，停止相关迁移，不能带着待确认项进入规则改写和最终切换。原规则副本只读使用，不继续编辑。
5. 重跑以下引用检索，保存实际命中，逐条分类为“现行入口 / 旧版历史说明 / 无关”。D24 在加注之前仍是待解决现行入口；名单外有效入口触发 `BLOCKED_SCOPE_DRIFT`，停止对应删除并申请有限增补。

```bash
rg -n --hidden 'bugfix\.md|feature\.md|refactor\.md' . \
  --glob '!.git/**' --glob '!.venv/**' --glob '!data/**' \
  --glob '!graphify-out/**'
```

**预期：** 原身份可回读、用户已有变更归属清楚、现行入口可迁移。`rg` 的 RC=1 只代表无匹配，RC>1 是失败；不能把旧文档中的字面命中当作现行断链。需要暂停用户未知修改时不自动清理。

## 5. Task 1：规则归一与参数事实源

**映射：** INV-01/02/04/06/08，S1/S2/S3/S6/S9/S14/S15/S17。**文件：** D01-D03、D24。

1. 在 D02 建立规则正文：保留安全和真实验证；写入 Design §4.1 的简短/正式链条件、§4.2 的措施触发与 Rule 17 新旧边界、§4.3 的测试和完成标准、§5 的修复分流。保留 15↔旧11、16↔旧12、17 的别名，不批量重编历史编号。
2. D01 将工程长条文改为短摘要和 D02 链接，保留 L0、L2、SSOT 及实际任务路由。只将 Design §3 的 30%/0.7/24h 镜像替换为三个准确配置标识符；48h、50%、70%、7d 等独立约束不动。不得借整理改 `RISK_LIVE_TRADING_ENABLED`。
3. D03 只保留最小充分修改原则和现有 `.agent/skills/ponytail/SKILL.md` 引用；删除重复阶梯及绝对 no-fixtures，保留数据损失、边界验证与已批准要求不能被 YAGNI 绕过。
4. D24 仅加醒目首页说明：这是旧版中文译本，正文保留用于历史阅读，不是当前指令入口；当前规则查 AGENTS/L1，本文旧 workflow 路径不再用于执行。这样解决入口冲突而不维护第二份完整规则正文。
5. 逐条核对旧规范→保留/集中引用/显式替换的对应关系，记录在现有 `execution-notes.md`；未获 Design 支持的删减不得实施。

**检查命令：** `git diff -- AGENTS.md AGENTS_CN.md .agent/rules/L1_Engineering_Process.md .agent/rules/ponytail.md`；`rg -n 'EXTREME_FUNDING_|RISK_LIVE_TRADING_ENABLED' AGENTS.md configs/base.py`。逐条走查 S1/S2/S6/S9/S14/S15/S17，反例为“离线即可绕过既有 profile”和“哈希一致即可证明计算正确”，均应被拒绝。

**预期：** 一份工程规则正文、可解析别名、三参数值及其他风险边界不变；高影响和旧契约仍有独立验证。失败先在本 Task 白名单内修正，不自动回到 Design。

## 6. Task 2：工作流收敛与旧入口退役

**映射：** INV-02/03/04/07，S4/S5/S10/S11/S16。**文件：** D01、D04-D07、D21-D23。

1. D04/D05 保留目标、事实假设、范围、决策、验收及适用的批准链；引用 L1 选择机制，不将 16 章、完整恢复/封存矩阵应用于每项任务。研究 Design 仍明确满足 L2 §15。任务按可独立验证的功能切分并注明依赖，不另生成 tickets。
2. D06 明确内部纯逻辑可使用合成输入、边界正向主张须有真实上游契约证据；期望值独立。全量 scanner/Graphify 不再逐 Task 无条件触发；保留相关改动与原 Plan 明定检查。上游 skill 调用前明确项目路径、禁止自动 commit 及批准边界。
3. D07 区分允许路径内修复、有限 Plan 增补、Design 语义变化。增补须检查 Plan/source bundle/授权/RUN_ID/证据依赖，不改绑旧输出；不能只因缺一测试路径就要求新 Design。保留真实 scope/spec drift 停止及用户决策。
4. D01 的 Bug 路由先定位根因，重构路由先证明行为保持；两者再按影响选择简短方案或四个正式 workflow。新功能同样分流。原命令名可以解释为任务意图，不指向已删文件。
5. 确认 D24 首页已生效于候选文本、现行引用清单无未解决项后，才删除 D21-D23。历史引用不批量改写。

**检查命令：** 重跑 Task 0 `rg`；`git diff -- .agent/workflows AGENTS.md AGENTS_CN.md`；逐一 `test -f` 四个保留 workflow，`test ! -e` 三个退役 workflow。命中必须逐项解释，不以全库零匹配为目标。

**预期：** S4/S16 只走必要的范围与证据更新，S5 仍返回 Design；旧入口无现行断链。名单外有效入口未解决时不得删除或判通过。

## 7. Task 3：三个项目技能及附属文件精简

**映射：** INV-02/03/04/05/06，S1/S2/S7/S8/S9/S12-S16。**文件：** D08-D18，精确到第 2 节各路径。

1. D08-D11 只负责 Plan 可实施性、范围、依赖、证据和必要检查；删除复制的 L1/L2 正文，保留指向及对研究数据/成本误用的具体案例。具体阈值案例标为案例输入，不升级为全库规则。
2. D12/D13 区分规范要求与事实证据；审查实际 index/worktree/untracked，不将 HEAD 无差异视为无实现。Rule 17 触发依 L1 和该任务冻结契约，不要求每个输出专用 verifier；`complete` 绝不授予 commit/deploy/runtime。只读报告在回复中交付，不默认增建 Recorder。
3. D14-D18 保留已有 OPEN、直接受影响证明边、新引入缺陷的返修边界；具体状态机/崩溃/封存矩阵只在真实契约涉及它们时使用。允许如实报告未关闭项，不能要求作者“全部 CLOSED”而迫使自证；不重开无新证据区域。
4. D15 删除解压覆盖整个技能目录、把完整规则复制到其他入口的建议；改为识别项目自有文件与上游来源，差分审查后定向更新。本任务不执行安装。
5. 在 D11/D13 中按各自职责引用 Design S1-S18 的固定预期，不抄第二份完整规范；原有其他案例保留或缩成相关反例，不因本轮不涉及资金就删除资金安全案例。

**检查命令：** `rg -n 'Rule 17|Rule 12|flock|fsync|四态|verifier|complete|fixture' .agent/skills/reviewing-implementation-plans .agent/skills/audit-plan-completion .agent/skills/closure-revision`；读取每个命中上下文，核对适用条件与权威引用。文件之间的 Markdown 相对链接用实际文件存在性逐条检查。

**预期：** 三个 skill 仍有可发现的 frontmatter/name 和单一职责；README/checklist/references 不偷偷恢复旧门禁；没有修改第三方 skill。此处是文字规则走查，不声称证明模型永不违规。

## 8. Task 4：Prompt 接线及来源说明

**映射：** INV-02/03/05/06/07/08，S8/S10/S12/S13/S18。**文件：** D19、D20。

1. D19 顶部解释简短任务不强制 A/B/C 全链，正式任务继续独立审核和明确批准；每个可复制 Prompt 必须自行保留最少权限边界和必读规则，不能只依赖复制时未包含的前言。
2. 同步 A-Intake/Plan/Revision/Audit、B 首审/复审、C 实施/返修和严格模式附录。删无条件固定 Task 编号、11 文件包、权限字段数量、flock/fsync/四态和专用 verifier 要求；替换为当前任务的实际契约及 L1 条件引用。保留精确批准 SHA、实际证据、独立审计、只修相关 finding。
3. Web B 缺仓库时上传关键规则原文及身份；缺什么只请求什么，不要求 GLOSSARY/ADR/spec/ticket 证明。模板不能要求 user 手工搬运仓库中可读取的证据，也不能猜未提供的 bytes。
4. D20 记录项目自有三个治理技能、外部 Superpowers/Ponytail/上下文/Graphify 文件族的实际来源线索、可证实版本、本地差异状态和项目适配位置。无准确版本写 `unverified`，不将文件头版本号当上游 commit；仅借鉴 Matt 方法不标成已安装技能。不下载、比较远端或更新任何技能。

**检查命令：** `rg -n '^## |flock|fsync|四态|Rule 17|Task|commit|runtime|SHA' docs/production_artifacts/tri_agent_prompt_library_CN.md`；逐个可复制代码块检查权限与 L1 路由；`git diff -- .agent/skills-sources.md docs/production_artifacts/tri_agent_prompt_library_CN.md`（新文件还须直接读取，不能只看 diff）。

**预期：** 不存在 Prompt 比 L1 更强的隐藏门禁或更弱的批准边界；来源未知被明确保留，不产生升级动作。

## 9. Task 5：独立验收与用户切换

**映射：** INV-01 至 INV-08，S1-S18 全集。**修改：** 执行者只维护声明的基线说明和候选哈希清单；独立审计者不写项目文件。

### 5.1 执行者提交事实

Tasks 1-4 每项结束按旧执行纪律检查 scope、实际 RC；本次迁移仍运行旧 scanner 门禁，不能用自己刚修改的豁免自证。未来文档任务的检查简化属于待激活新规则，不追溯消除此处检查。

```bash
git status --short --untracked-files=all
git diff --name-status "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git ls-files --others --exclude-standard
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
```

逐条记录实际 process RC；不要通过 `tee` 等丢失原进程返回值。scanner 非零停止；warning 在同一执行说明中记录原因，不另造 JSON ledger。纯文档无业务 pytest、Ruff 或 raw replay；Graphify 仅查询不 update。上述检查只是必要证据，不能代替下述路由核验。

将当前候选文件（D01-D20、D24）的 SHA 写入 `candidate-sha256.txt`，D21-D23 记录为预期不存在；保存当前 Design/Plan identity、范围及未决问题，不写“独立审计已通过”。既有 untracked Design/Plan 不是本次越界实现；必须证明其 bytes 未变。`git rev-parse HEAD` 必须仍等于 `BASE_SHA`，index 与 Task 0 完全一致，不自动暂存；发现其他会话改动时停止并报告，不擅自重定基线。

### 5.2 独立审计

新独立 session/用户从 `old-authority/` 读取旧权限、执行纪律和 audit skill，以已批准 Design/Plan 为变更目标。候选审核技能只作为被审对象，不作为本次审查权威。通过固定旧文件身份定位入口，不误调用工作区新版。B 无仓库时传输同组原文和 SHA。

审计重新读取实际 diff、index、untracked、旧文件副本和候选 bytes；独立运行上面的检查及本地只读安全断言（`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'`）。不接受 C 的 GREEN 摘要代替这些证据。

对 Task 0 的未跟踪治理来源分类，审计员独立重跑 `git ls-files --others --exclude-standard`，与执行前 `untracked-paths.txt`、实际引用/加载依据及现有差分交叉核对，区分原有文件与本 Plan 新建的 D20，不将新文件追溯补成旧基线。逐项检查确认适用的原有文件均有可读副本、相符 SHA 和来源依据，确认无关的分类有事实支持；不能只核对执行者挑选的 `old-authority-paths.txt` 或相信“所有旧规则已保存”。未解释的遗漏、待确认分类、缺失/不符的副本或新增治理来源，均阻止 `complete` 和切换；只请求对应缺失证据或修复，不补造旧 bytes，也不因此扩大 D01-D24 修改范围。

| 验收组 | 对应 Design 场景 | 必需证据与拒绝情况 |
|---|---|---|
| 测试与计算 | S1/S2/S3 | 纯逻辑可合成，跨边界正向证据真实；可重算仍验证语义，不强制无关锁 |
| 任务路由 | S4/S5/S6/S16 | 增补不等于设计变化，白名单不许可语义变化，旧绑定不被自动升级 |
| 审计边界 | S7/S8/S12 | 真实工作区范围、有限复审、精确缺证据请求；风格偏好不阻断 |
| 历史/资金 | S9/S10/S14/S15/S17 | 新旧 Rule 17 区别清楚、旧 profile 不降级、三参数仅引用、权限不增加 |
| 切换/链接 | S11/S13/S18 | 现行入口可达、候选不自审、中断不激活、验收后改动失效 |

以获批 Design 场景为 oracle（预期依据），不以改后的 skill 自产预期。对每个场景记录实际入口、适用规范、预期动作和发现的矛盾；正向读取保存的真实旧规则及真实候选文件，反向使用 Design 已有的未授权、身份变化、错误自证案例进行文本走查。不得把文本走查或示例参数称为运行时/市场实验。

本次不生成或修改跨边界机器产物 profile。普通 Markdown 规范、基线副本和人工 SHA 清单不是 J-C receipt；既有 Rule 17 对人类 Markdown 的例外适用，不为本迁移开发/运行专用 schema verifier。真实 crash/recovery 程序亦 N/A；恢复验证限 S18 和下面的文档恢复步骤。

独立审计只有在 Tasks 0-4 和 5.1 的实现交付、全部 INV/S 场景、范围、引用及只读边界有证据时才可给 `complete`，范围限定为实施验收；5.3 是其后的用户生效决定，不反过来作为本次审计前提。报告在回复中给出候选清单/SHA、基线、actual RC 与剩余问题；不要求审计员落盘。发现问题按第 10 节路由，修复后只重验受影响部分及最终身份。

### 5.3 用户接受后才生效

独立验收 `complete` 表示迁移实现完成，**不等于新治理已经激活**。等待用户明确接受审计对应的候选版本并宣布新任务生效；接受前重算文件 SHA、核对删除集及无额外改动。若不一致，返回受影响复核，不能接受旧结论。

生效后重新加载规则或使用新会话；旧批准任务仍使用原契约。用户暂不接受时保持维护暂停，或另授权恢复本次治理变更后解除暂停。此阶段不需要专门授权程序、commit、部署或研究 runtime；无论是否完成，本 Plan 都不授予这些动作。

## 10. 停止、恢复与验收映射

| 情况 | 最小动作 |
|---|---|
| Design/Plan SHA 或批准范围不符 | `approved_authority_mismatch`；不写规则 |
| 维护窗口未确认、旧规范副本缺失/不一致 | 停在 Task 0；不能只记录不确定性后继续 |
| 白名单内没有实现已批准要求 | `BLOCKED_IMPLEMENTATION_DEFECT`；定向修复与复核，不新建 Design |
| 多出有效入口或必须改白名单外文件 | `BLOCKED_SCOPE_DRIFT`；停止对应动作，请求有限 Plan 增补；不擅自利用尚未生效的新规则 |
| 必须改变获批治理目标、授权边界或历史契约 | `BLOCKED_SPEC_DRIFT`；给出具体矛盾，返回 Design 决策，不扩大本 Plan |
| 中断、部分修改或验收失败 | 维持暂停；先比对旧副本与当前改动，再在本 Plan 内继续修复或请求恢复 |
| 用户批准恢复 | 只恢复有归属证明的本次修改；用 `old-authority/` 比对并恢复原 bytes，保留用户原 dirty/index；新建 D20 仅在证明本次创建且未被他人修改后移除。核对旧入口全在、旧规则一致后解除暂停；不覆盖异常改动、不用全库 reset |

Task 0 复制中断时，不修改规则；保留部分基线，重新建立完整基线。规则已修改后中断，不得把当前混合版本重新定义为“旧基线”；继续使用原 Task 0 副本。若副本缺失，停止并请求精确缺失证据，不凭记忆重构。

| Design invariant | 实施 owner | 核验 |
|---|---|---|
| INV-01 权限/L0/L2/研究不变 | Tasks 0/1/5 | scope、原 bytes、安全断言，S6/S9/S10/S17 |
| INV-02 单一工程正文 | Tasks 1-4 | AGENTS→L1→workflow/skill→Prompt 实际引用；旧规范映射 |
| INV-03 修复及证据继承 | Tasks 2/3/4 | S4/S5/S16，无自动改绑或范围放大 |
| INV-04 主张与证据一致 | Tasks 1/2/3 | S1/S2/S3/S14，独立语义预期 |
| INV-05 实际变更与有界审核 | Tasks 3/4/5 | S7/S8、index/untracked、actual RC |
| INV-06 上游/历史 bytes 不变 | Tasks 0/1/3/4/5 | 基线副本/原 SHA 与 scope；S9/S10 |
| INV-07 入口及附属文件一致 | Tasks 0/2/3/4/5 | D24 增补、反向引用、保留/退役路径检查、S11/S12 |
| INV-08 生效隔离及显式 Rule 17 调整 | Tasks 0/1/4/5 | 旧审查依据与新规格分离，S13-S15/S18，用户接受版本 |

本 Plan 的完成标准是上述文档改动与独立验收，不要求证明模型永久服从或实现全仓库无缺陷。行数/token 不设硬门槛。不实施外部技能升级、不复开 J-C 研究、不为了保存审计报告再建治理系统。

下一步：B 独立审核本候选（包含 D24 范围增补）；用户批准精确 Plan bytes 后才可执行 Task 0。作者自查不是 B 批准。
