# 新合约主动买入占比与剩余价格响应 Implementation Plan

> 执行者仅在本 Plan 独立审查通过且用户明确批准实施后，按 `.agent/workflows/execute-approved-plan.md` 执行；不得自动提交。

**Goal：** 实现单一首分钟主动买入占比与入场后 15 分钟价格响应的离线探索，维持 Parent 分母、时间先后和上游权限边界。

**Architecture：** 一个研究模块负责纯计算、经准入的只读归约及汇总；一个 CLI 只负责显式参数、独立授权前置检查和新目录输出。纯逻辑测试使用最小合成数据；真实上游正向准入和全量运行是另行授权的独立门禁。输出是探索性明细与人类报告，不授予机器消费或交易权限。

**Tech Stack：** Python 标准库、项目现有公开 J-A/J-B strict loader 与 ZIP validator、pytest、Ruff。

**Design binding：** `docs/designs/2026-10-31-launch-taker-buy-share-residual-response-exploratory-design_CN.md`，SHA-256 `5c05cb304da482bf5c29c0f98938795e11949b4130149474b6f8842175684896`。批准 Plan 不授权历史数据消费或运行；以当前 Plan 实际 SHA 绑定单次运行授权。

## Allowed Change Scope

| 类型 | 精确范围 |
| --- | --- |
| Allowed implementation paths | 新增 `src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py`；新增 `scripts/external_signal_shadow/run_launch_taker_buy_share_residual_response.py`。 |
| Allowed verification paths | 新增 `tests/research/external_signal_shadow/test_launch_taker_buy_share_residual_response.py`；新增 `tests/scripts/external_signal_shadow/test_run_launch_taker_buy_share_residual_response.py`。 |
| Allowed documentation paths | 无；本 Plan 与已批准 Design 保持原字节。 |
| Allowed generated/runtime artifacts | 默认仅 pytest `tmp_path` 与执行者记录用临时目录；**经独立运行授权后**才可在用户批准的一个不存在的新本地目录内生成 `child_rows.csv`、`review_CN.md`。该目录不得位于上游 root、工作区受跟踪路径或其祖先，不得覆盖任何已有文件；无其他正式 receipt。 |
| Affected but unchanged | J-A/J-B/J-C 源码、测试、原始 ZIP、receipts、closure evidence、V2 ledger、配置及冻结 Design；通过身份核验与状态对比证明未修改。 |
| Forbidden | 白名单外修改、全库自动格式化或清理、上游重生/迁移、网络、SSH、deployment、commit/push、策略信号、paper/live/execution；不得读取 J-C validation-only 临时输出作为输入。 |

新研究输出仅供人工阅读及人工复核，不属于 J-A/J-B/J-C 冻结 profile。不得声称通过旧 Rule 17 profile；如未来用于机器跨阶段消费须另行定义契约。本次不新增专用独立 verifier 或 Recorder。

## Task 0：基线与权限前置

**依赖：** 用户批准本 Plan。**对应：** `INV-01`、`INV-02`。**文件：** 无仓库文件修改。

1. 从用户**实际实施批准语句**读取 Plan path 和 SHA-256，与当前 Plan 精确路径及实时计算的文件 SHA 比对；不得从当前文件反推用户批准值。任一不符或用户批准语句缺失即 `STOP=approved_plan_authority_mismatch`，不得进入实施。包含仅更改 Plan 一个字节的负向演练须在 `tmp_path` 副本执行，证明比对非零退出且不进入任务，不修改已批准文件。
2. 在新建临时目录记录 `BASE_SHA=$(git rev-parse HEAD)`、`git status --short --untracked-files=all`、`git diff --binary` 和 `git diff --cached --binary`，不覆盖既有证据。使用 `git ls-files --others --exclude-standard -z` 捕获执行前全部未跟踪路径，以 NUL 安全方式逐项记录路径、文件类型及常规文件 SHA-256；符号链接记录链接目标而非跟随，无法读取则停止并报告。Design/Plan 若为未跟踪文件也纳入，不将其算作本次新增文件。对每个预期新增路径检查不存在，若已存在则停止，不覆盖。
3. 计算 Design SHA 并与本 Plan 精确匹配；核对 `configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED is False`。读取 [J-C Design §2.1/§4](../designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md) 与 J-A/J-B 上游冻结条款，记录固定根和身份；仅做静态检查，不调用会重放历史数据的 strict loader。
4. 写清独立消费门：Task 1–3 只能使用测试自建输入。真实 J-A/J-B loader、canonical 正向准入、完整历史运行及报告生成必须先取得用户**另行明确**的单次离线消费/运行授权，确认 Design/Plan SHA、上游根、输出根和操作范围。文件存在、hash 正确或命令行 flag 不等于用户授权。

执行并保存实际返回码：

```bash
BASELINE_DIR=$(mktemp -d "${TMPDIR:-/tmp}/taker-share-baseline.XXXXXXXX")
BASE_SHA=$(git rev-parse HEAD)
printf '%s\n' "$BASE_SHA" > "$BASELINE_DIR/base-sha.txt"
git status --short --untracked-files=all > "$BASELINE_DIR/status.txt"
git diff --binary > "$BASELINE_DIR/worktree.patch"
git diff --cached --binary > "$BASELINE_DIR/index.patch"
git ls-files --others --exclude-standard -z > "$BASELINE_DIR/untracked.paths"
python3 - "$BASELINE_DIR" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

baseline = Path(sys.argv[1])
paths = (baseline / 'untracked.paths').read_bytes().split(b'\0')
records = []
for raw in filter(None, paths):
    p = Path(os.fsdecode(raw))
    if p.is_symlink():
        records.append({'path': str(p), 'type': 'symlink', 'target': os.readlink(p)})
    elif p.is_file():
        with p.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        records.append({'path': str(p), 'type': 'file', 'sha256': digest})
    else:
        raise SystemExit(f'unsupported_or_missing_untracked_path: {p}')
(baseline / 'untracked.json').write_text(json.dumps(records, ensure_ascii=True) + '\n')
PY
shasum -a 256 docs/plans/2026-10-31-launch-taker-buy-share-residual-response-exploratory-implementation-plan_CN.md
shasum -a 256 docs/designs/2026-10-31-launch-taker-buy-share-residual-response-exploratory-design_CN.md
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
```

预期全部 `RC=0`；`BASELINE_DIR` 为执行者刚创建、此前不存在的临时目录，快照步骤及未跟踪文件清单须各自记录实际 RC；上例的 `hashlib.file_digest` 需 Python 3.11+，否则以 `.venv/bin/python` 执行该块或采用分块 `hashlib.sha256().update()`，不得遗漏记录。Plan hash 比对用户批准值、Design hash 比对 binding 值，分别失败即 `STOP=approved_plan_authority_mismatch`、`STOP=design_authority_mismatch`。身份不匹配不得现场替换冻结期望；上游契约不允许新 consumer 时 `STOP=BLOCKED_SPEC_DRIFT`。单次历史授权缺失不是允许伪造的测试数据，保留 `historical_validation_not_authorized`。

## Task 1：单 child 特征与延迟路径

**依赖：** Task 0。**对应：** `INV-02`、`INV-03`、`INV-04`、`INV-06`。**文件：** 研究模块、研究测试文件。

采用 RED → GREEN：先写 `test_feature_and_path_hand_calculated`、`test_time_order_and_endpoint_boundaries`、`test_unavailable_and_gap_states`，执行以下命令确认因功能缺失而 RED，再实现并确认 GREEN：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_launch_taker_buy_share_residual_response.py \
  -k 'feature_and_path_hand_calculated or time_order_and_endpoint_boundaries or unavailable_and_gap_states'
```

预期 GREEN `RC=0`；先记录实际 RED，不能因测试导入或 fixture 拼写错误冒称 RED。测试直接调用模块公开的纯计算入口，输入按 `(timestamp_ms, aggregate_id)` 严格递增的成交序列，输出特征、entry、endpoint、terminal/MAE/MFE 和 Design §4.2 状态。

研究时间常数由 CLI 内部的固定描述性协议传入研究模块，不在 `src/` 中散布时间魔数，不暴露命令行参数或可调策略配置；纯函数接收协议作为输入并检查其与获批 Design 一致。不新增 `configs/` 模块或修改 `configs/base.py`。实现和独立预期至少覆盖：

- `T0=0` 时，特征成交 `(p=100,q=2,buyer_maker=false)`、`(p=110,q=1,buyer_maker=true)` 的主动买入金额占比为 `20/31`、VWAP 为 `310/3`、最后成交 VWAP 偏离为 `2/31`；用 `Decimal`/`Fraction` 或等价精度保留未舍入判断。
- `[T0,T0+60000)` 排除恰在 60000ms 的成交；entry 接受 63000 和 64000ms、拒绝 64001ms；`T_end=entry.time+900000ms`，endpoint 包含 `T_end-1000ms` 与 `T_end`、排除之后；同毫秒按 ID，entry 之前记录不进路径。
- entry 100、终点 110、期间最低 90 最高 120 的手算结果为 `terminal_return=0.1`、`long_mae=-0.1`、`long_mfe=0.2`；没有 feature/entry/endpoint、ID 断档、跨 UTC 午夜缺包分别产生 Design 状态而非填零。非法价格、顺序倒退等是错误而非业务缺口。

上述向量仅为模块内纯计算，不得称为真实上游兼容证据。

## Task 2：分组、Parent 与敏感性切片

**依赖：** Task 1。**对应：** `INV-02`、`INV-04`、`INV-05`、`INV-06`。**文件：** 同 Task 1。

先增加 `test_group_parent_and_ties`、`test_leave_one_parent_out_recalculates_and_null`，用以下命令 RED → GREEN：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_launch_taker_buy_share_residual_response.py \
  -k 'group_parent_and_ties or leave_one_parent_out_recalculates_and_null'
```

预期 GREEN `RC=0`。同机制仅使用特征与路径均 complete 的 child 作 child 中位数分组；缺口留在总分母。Parent 以 `(parent_article_id, listing_regime)` 分组，只有该组全部 universe child complete 才产生 Parent 中位数，按 Design §3.4 重新以 Parent 中位数分组、等权汇总；跨机制同 Parent 仍是一个公告簇。中位数相等归 low，不人为拆开；空组结果为 `null` 并标注 `evidence_insufficient`。

独立向量：三个完整 Parent 的特征为 `1/4, 1/2, 3/4`，对应 `terminal_return=0.1,0.2,0.4`；原 high 均值减 low 均值为 `0.25`。剔除最后一个 Parent 后重新算分界为 `3/8`，差异为 `0.1`。另测剔除后无 high 组时差异 `null`；每次保留剔除 ID、剩余总数、组数和差异，报告全部非 null 范围，不按结果挑 Parent。统计 `P25/P75` nearest-rank、偶数中位数取两项均值。

## Task 3：准入、只读归约与报告

**依赖：** Tasks 1–2。**对应：** `INV-01` 至 `INV-06`。**文件：** 全部四个允许路径。

1. 新 CLI 默认拒绝实际历史运行；只有在控制执行者确认单次用户授权内容与 Design/Plan SHA、J-A/J-B 固定根及新的输出路径一致后，才允许显式运行。CLI 必须先检查用户提供的授权文件包含上述精确身份、操作 `offline_research_once` 和 `network/paper/live/execution=false`，不匹配、缺失或输出路径已存在时在调用任何 loader/打开 raw 前非零退出；CLI 检查是防误用，授权文件本身不能证明用户身份，独立审核者须核对用户原始批准消息。单次授权不得复用其他研究的 release，也不得因批准本 Plan 自动生成。创建输出目录前检查既存祖先，拒绝任何符号链接祖先；以物理规范路径比较，禁止输出位于任一受保护输入 root 内、等于它或为其祖先，亦遵守本 Plan 的其他输出范围限制。对最终新目录使用排他性新建（例如 `mkdir(exist_ok=False)`），已存在即拒绝；不创建或写入上游 root。
2. 经授权后才延迟调用 `load_verified_stage1_5j_a_historical_archive_coverage_root(Path)`、`load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(Path)`、`validate_zip_archive_package(Path)` 及适用的 J-A closure admission；检查 J-C Design §2.1 的固定根、manifest/summary/review、ledger 和既有 upstream closure authority。V2 ledger 必须先验证精确 SHA-256 `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` 与 J-C Design §4.1 冻结的 12 列精确结构；分类字段只能来自该已核验文件。J-B 返回的 `source_article_id` 映射 `parent_article_id`、`anchor_time_ms`/`anchor_price` 必须由同 Parent/symbol 的 raw 重证；ledger 联合键唯一且与 J-B child 集合双射。禁止使用 J-B 私有 reader、手工 package record 代替真实准入。
3. 依据获准 J-A `archive_package_records` 确定 Parent/symbol/UTC 日份，流式核对路径、CHECKSUM、SHA、ZIP 结构/资源限制、CSV 合法性、ID 与时间顺序并读到 EOF/CRC；不得只依赖 J-B 1h 包级状态或自行拼路径猜测。导入已冻结 `EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES`（65,536 bytes）作为底层读取与包含换行的物理 CSV 行上限；有界读取在完整超长行进入内存前检测并拒绝，不借用 J-B 私有 reader，也不以 ZIP 元数据预检代替行限制。跨日所需包不存在时保留 `required_package_unavailable`；宣称存在但损坏或身份错误时全次停止。实时计算所需日期直至 `entry.timestamp+15min`，不超出 Design 时间窗口。
4. 输出只在单次授权批准的新目录中创建；先完成输入校验和全部归约，再写 `child_rows.csv` 和 `review_CN.md`，失败时非零退出，不得将部分输出标为成功或覆盖已有内容。报告写入 Design/Plan 身份、上游身份、时点/分组定义、样本守恒表、缺口、两机制 Child/Parent 汇总、全部 leave-one-out、未覆盖限制与 `exploratory` 标记；不包含下游使用或交易授权。

先写 `test_authorization_denied_before_loader`、`test_output_collision_and_no_false_success`、`test_summary_structure_and_conservation`、`test_ledger_classification_tamper_rejected`、`test_oversized_csv_line_rejected`、`test_output_symlink_ancestor_rejected`、`test_canonical_upstream_positive`、`test_canonical_single_mutation_rejected`。前六项只使用 `tmp_path` 和故障注入；后两项是需要真实上游字节的正向准入及单点变异验证，不得由手工合成 record 替代。分类篡改测试仅修改 ledger 副本的 `listing_regime`，保持联合键不变，证明 SHA 校验拒绝；超长物理行测试证明读取有界、非零退出且无成功报告；符号链接测试将输出祖先指向临时受保护输入根，证明拒绝且该根无写入。受限测试的 fixture 在缺少单次授权时应显式 skip，不能产生正向通过结论；记录 skip，而不是把它计入完成证据。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_launch_taker_buy_share_residual_response.py \
  -k 'authorization_denied_before_loader or output_collision_and_no_false_success or summary_structure_and_conservation or ledger_classification_tamper_rejected or oversized_csv_line_rejected or output_symlink_ancestor_rejected'
```

预期 `RC=0`，否定授权测试以调用计数证明 loader/raw 未被触碰。额外对输入损坏、缺包、重复键、跨日、完整分母及预期数值进行局部回归。报告字段由独立手算向量或独立计算验证，不由生产 reducer 同一函数自证。

### Task 3B：另行授权后的真实正向门禁

**依赖：** Task 3 合成门禁通过、用户另外明确批准一次离线消费/运行、授权绑定的当前 Plan/Design/输入/输出身份一致。**本 Plan 实施批准本身不触发本步骤。**

- 受控执行者先向用户给出具体操作范围、两 root、输出路径及 Design/Plan SHA；用户明确同意后独立核验原始批准消息并创建测试使用的授权文件。禁止用执行者自造文件冒充用户同意。
- 正向用真实 closure-audited J-A/J-B 根及 ledger，通过公开 strict loaders 和实际新 consumer，至少重证一个真实完整 child；从已准入 package 复制到 `tmp_path` 后做单点哈希/身份变异，确认拒绝，原 root 不写入。
- 执行并记录实际 RC：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/scripts/external_signal_shadow/test_run_launch_taker_buy_share_residual_response.py \
  -k 'canonical_upstream_positive or canonical_single_mutation_rejected'
```

预期 `RC=0` 且两项实际运行而非 skip。仅当单次授权还明确包含完整研究归约与报告生成，才可按授权中的输出根调用新 CLI；仅授权 canonical 测试不等于授权全量运行。授权缺失或上游不合规则保留未验证状态、停止，不制造完成结论。

## Task 4：验收与独立审计

**依赖：** Tasks 1–3；涉及历史结论的完成还依赖 Task 3B 的真实正向和另行授权运行。**对应：** 全部 `INV-01`–`INV-06`。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q \
  tests/research/external_signal_shadow/test_launch_taker_buy_share_residual_response.py \
  tests/scripts/external_signal_shadow/test_run_launch_taker_buy_share_residual_response.py
.venv/bin/ruff check src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py \
  scripts/external_signal_shadow/run_launch_taker_buy_share_residual_response.py \
  tests/research/external_signal_shadow/test_launch_taker_buy_share_residual_response.py \
  tests/scripts/external_signal_shadow/test_run_launch_taker_buy_share_residual_response.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git diff --check "$BASE_SHA"
git status --short --untracked-files=all
```

记录每条命令的**实际进程 RC、测试通过和 skip 数**；Ruff、scanner 和 `git diff --check` 均需 `RC=0`。检查 staged/unstaged/untracked 与 Task 0 基线，逐项重算并比对执行前未跟踪文件的类型、SHA 或链接目标，解释变化并核对是否获准；区分已有 Design/Plan 和四个新增实现文件，不将空 diff 视作无未跟踪文件。核对上游根、配置和已有研究代码未修改；发现白名单外改动停止，不清理用户文件。

独立完成审计按目标、scope、时间语义、独立手算、输入权威与实际执行证据分别裁定：

- 未取得单次授权或 canonical 正向未运行：至多 `implementation_ready / historical_validation_incomplete`，不得声称全 Plan 或历史研究 `complete`。
- 取得授权后仍需核对真实正向 RC、输出结构、逐 child 守恒、Parent 聚合与独立手算证据；不得只接受执行者的测试摘要。历史结果仍为探索性，不授予新 consumer、交易或部署权限。
- 白名单内实现偏差按 `BLOCKED_IMPLEMENTATION_DEFECT` 修复；纯范围扩展按 `BLOCKED_SCOPE_DRIFT`；若需改变批准研究语义或冻结上游权限按 `BLOCKED_SPEC_DRIFT` 停止。审计与任何批准都不自动授权 commit/push、deployment、SSH、paper/live 或后续运行。
