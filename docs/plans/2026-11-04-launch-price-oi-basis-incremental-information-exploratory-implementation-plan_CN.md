# 新合约价格状态与 OI／基差增量信息有限探索 Implementation Plan

**状态：** `plan_candidate`，待独立审查和用户实施批准。本文不授权代码修改、真实快照读取或研究运行。

**Goal：** 用一个新分析脚本及其测试实现获批 Design 的固定 Parent 级增量比较，不重建旧数据管道。**Architecture / Tech Stack：** Python 标准库负责 CSV、身份和路径；已安装 NumPy 负责 OLS；数据用简单记录，不新增依赖、通用模型框架或配置模块。

**Design binding：** [新合约价格状态与 OI／基差增量信息有限探索 Design](../designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md)，SHA-256 `f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e`。用户已明确接受其 §2 精确快照受限消费契约；这不等于实际消费授权。原 OI Design/Delta/Plan 只按该 Design 追溯，不继承旧运行许可。

## Allowed Change Scope

| 类别 | 精确路径或边界 |
| --- | --- |
| Allowed implementation paths | 新建 `scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py`，下称 `SCRIPT`。 |
| Allowed verification paths | 新建 `tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py`，下称 `TEST`。 |
| Allowed documentation paths | none；执行时不得修改本 Plan、获批 Design 或其他文档。 |
| Allowed generated/runtime artifacts | 实施期仅测试 `tmp_path` 和工作区外的执行前基线/命令记录；收到适用的用户实际操作授权后可在工作区外机械转录为机器授权记录，不得添加原文没有的动作或路径；若另获实际运行授权，仅在用户指定全新目录生成 `parent_panel.csv`、`fold_diagnostics.csv`、`review_CN.md`。 |
| Affected but unchanged | 旧 OI 研究模块及 CLI/测试、Design §2 指定 CSV/报告、旧契约、L0/L1/L2、配置、依赖声明、J-A/J-B/J-C 与 raw。旧 writer 的格式兼容通过临时 canonical 夹具验证，不修改其函数。 |
| Forbidden | 白名单外变更、读取未授权真实快照或 raw、下载/联网、全库格式化或清理、修改风险参数、重构旧模块、Graphify 输出更新、独立 Verifier/Recorder/锁/恢复状态机、git add/commit/push、部署、SSH、signal、shadow 策略、paper/live/execution。 |

使用 `execute-approved-plan`、TDD 与 `verification-before-completion` 时以项目规则为准，禁止上游技能的自动提交/自动执行默认动作。每个行为切片先写可解释的 RED，再最小 GREEN，最后必要 REFACTOR；记录实际 RC。以下命令均为未来批准后的执行步骤，本次起草不运行这些实施测试。

## Task 0：批准身份与执行前基线

**依赖：** 本 Plan 获独立审查和用户实施批准。**文件：** 无仓内修改。**不变量：** INV-01、INV-06。

- [ ] 从用户原始批准语句核对本 Plan 路径/SHA 与上述 Design binding；同时保留用户已接受 Design §2 的语句。身份不符 `STOP=approved_authority_mismatch`，不得从磁盘存在反向推定许可。
- [ ] 在工作区外临时目录保存实际 `BASE_SHA`、HEAD、status、staged/unstaged patches、未跟踪文件路径/类型/内容 SHA 和符号链接目标，保护现有 Design/Plan 等用户文件。当前起草时 HEAD 为 `8ccabb49e876839c5bcf8069089072a3acaf3bb9`，仅作背景，执行基线以真正开始时为准；执行期 HEAD/既有文件发生未预期变化即停查，不覆盖或回退。
- [ ] 确认两个新路径未被其他工作占用，检查旧 `ChildEvaluation`、`aggregate_and_group`、`write_exploratory_outputs` 源码及现有 NumPy 可用性。不能调用旧 `execute_exploratory_pipeline` 或读取历史快照来完成 baseline。

```bash
git rev-parse HEAD
git status --short --untracked-files=all
git diff --binary
git diff --cached --binary
shasum -a 256 docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md
test -n "${USER_APPROVED_PLAN_SHA256:-}" &&
test "$(shasum -a 256 docs/plans/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-implementation-plan_CN.md | awk '{print $1}')" = "$USER_APPROVED_PLAN_SHA256" &&
test "$(shasum -a 256 docs/designs/2026-11-04-launch-price-oi-basis-incremental-information-exploratory-design_CN.md | awk '{print $1}')" = "f38fd9c4609a52cc9d2d6529cceabca35c778e84c374fad4e386029d0493519e" || {
    printf '%s\n' 'STOP=approved_authority_mismatch'
    exit 1
}
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -c 'from configs import base; assert base.RISK_LIVE_TRADING_ENABLED is False'
```

`USER_APPROVED_PLAN_SHA256` 必须从用户本次实际批准语句原样提取，不能从当前文件计算后回填，也不能使用本轮审查前的旧 Plan SHA；未收到批准语句时不得执行实施任务。预期命令 `RC=0` 且 Design/Plan 两个 SHA 都精确匹配相应批准身份；缺批准、无法核验或不一致均 `STOP=approved_authority_mismatch`，不得继续 Task 1 或填入 Task 3 的授权绑定。补充的未跟踪内容快照不可仅用空 `git diff` 代替。

## Task 1：canonical 输入到 Parent 面板

**依赖：** Task 0。**文件：** SCRIPT、TEST。**不变量：** INV-01、INV-02、INV-03、INV-06。

**接口：** `load_snapshot(csv_path: Path, *, expected_sha256: str) -> list[dict]` 负责哈希及 Design §2 全部字段/状态规则；`build_parent_panel(rows: list[dict]) -> list[dict]` 返回全部 `(regime,scenario,parent_article_id)` 的聚合、完整资格和缺口记录。参数化 hash 用于内部接口与合成测试，实际 CLI 必须传 Design 的固定哈希，不能向用户开放忽略验证或任意预期 hash 的开关。

- [ ] TEST 内用旧模块公开 `ChildEvaluation` 构造最小合成 child，调用 `aggregate_and_group` 与 `write_exploratory_outputs(out, children, result, project_root=tmp_path)` 生成 canonical CSV；不调用真实 loader、ledger 或 raw。聚合结果仅用于让旧 writer 产生标准产物，**不作为新面板或模型的预期 oracle**；也不照抄旧私有测试工厂。writer 来源与字段映射以 Design §2 为准。
- [ ] 完整夹具显式设置有效日期、有限 baseline/y/MAE/MFE、路径及 A/B/C 的 `ok` 状态和各自有限 OI 值，B 通用别名与显式 B 值一致、`is_complete=true`、`missing_reason` 为空；基差成功时设置 `ok` 加有限值，缺失时仅设置 `unverified_product_mapping` 加空值。缺锚点夹具按 Design §2 的完整缺失分支生成，不让 writer 的可选默认值意外制造非法正向样例。
- [ ] RED：`test_snapshot_canonical_contract_and_mutations` 正向接受 canonical writer 格式。分别单点测试坏 SHA、缺/重复列、行长度不匹配、重复联合键、未知机制/状态、`ok` 配空或 NaN/Inf、B 别名不一致、缺锚点配有限结果、基差空状态出现在非缺锚点行、PIT/解释标签被升级。语义负向测试可给内部 loader 传变异夹具的实际 hash，避免只命中坏 SHA；实际入口篡改测试仍应先命中固定 hash 拒绝。
- [ ] RED：`test_parent_panel_conservation_and_dates` 手算同 Parent 三个完整 child：`p=(0.1,0.3,1.1)`、`o_B=(0.2,0.6,1.9)`、`y=(-0.1,0.3,0.9)`，Parent 中位数应为 `0.3/0.6/0.3`，能识别误用均值或只选赢家；另以两个值 `p=(0.1,0.3)` 验证偶数中位数为 `0.2`。另一 Parent 含一个完整和一个合法缺锚点 child，应整体不进入完整集合且保留候选分母；基差单项缺失只移出 `basis_complete`。覆盖不同机制、同 Parent 跨机制、唯一已知日期、全缺日期及多日期冲突；断言完整/缺失分母相加等于 Universe。
- [ ] GREEN：严格按 Design §2 与 §3.1 实现。A/B/C 逐列读取，不用 B `is_complete` 统一过滤；基差有效性仅为 `basis_status=ok` 加有限值。明确列出 `oi_complete`、B 的 `basis_complete` 资格；保留所有候选 Parent、child 数与原因。canonical 小样例不必凑 71/69/59 行；真实消费也不能硬编码结果数量来伪造成功。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py -k 'snapshot or parent_panel'
```

RED 应由具体状态/数值/聚合断言失败，不只记录 import 失败；GREEN `RC=0` 且实际选中上述测试。

## Task 2：面板到固定 cohort 模型比较

**依赖：** Task 1。**文件：** SCRIPT、TEST。**不变量：** INV-02、INV-03、INV-04、INV-05。

**接口：** `evaluate_comparisons(panel: list[dict]) -> list[dict]` 返回所有应有折及 `ok/not_estimable` 状态；`summarize(panel: list[dict], folds: list[dict]) -> dict` 返回集合计数、模型对指标、分布和贡献诊断，不作交易结论。无需新建模型基类或注册表。

- [ ] RED：`test_models_independent_affine_vector` 使用 `p=(-3,-2,-1,0,1,2,3,4)`、`o=(2,-1,3,0,-2,1,4,-3)` 和独立公式 `y=1+2*p`。对可估折，M0/M1 留出预测均应等于该公式、误差近零，预期不得调用被测 OLS 生成。再用 `y=1+2*p+3*o+4*p*o` 验证 M1 能还原独立交互公式；不要将“训练拟合一定改善”当作 OI 证据。
- [ ] RED：`test_models_independent_basis_vector` 沿用上述八个 Parent 的 p/o，增加 `b=(1,-2,0,4,-1,2,3,-3)`，用独立公式 `y=1+2*p+3*o+4*p*o+5*b` 得到 `y=(-18,-8,-4,21,-16,26,82,-63)`。八折 M2 训练均为 7 行、5 列且满秩；逐折预测必须接近对应已知 y，实际误差近零，不能调用被测模型生成预期。特别留出第四项 `(p,o,b,y)=(0,0,4,21)` 时，训练 b 均值为 0、总体标准差为 2，留出 `z_b=2`，标准化后的基差系数应为 10；直接检查该折训练标准化参数/设计列及基差项贡献，防止仅因 OLS 的缩放不变性让错误的全样本标准化漏检。该折同子集 M1 的独立精确预测为 `-310243/384032`，不是 21；`M2_vs_M1` 的实际预测误差增量应接近 `(21+310243/384032)^2`。检查实际 M1/M2 预测及其误差进入比较，不能只验证 comparison 名称或预制误差数组；仅在测试内观察必要矩阵/系数，不为此新增生产接口、报告字段或持久化证明文件。
- [ ] RED：`test_fold_training_only_and_estimability` 核对每折训练范围及标准化。手算训练 `p=(0,2,4)` 的均值为 2、总体标准差为 `sqrt(8/3)`；改变留出行不得改变训练参数，改变留出 y 不得改变其预测。覆盖同 Parent 跨机制全部剔除、零方差、秩不足、训练行数等于列数、空 cohort；不得加入正则、回退模型、筛掉坏折或填 0。
- [ ] RED：`test_cohort_keys_and_basis_pairing` 构造至少 10 个标准 Parent，其中 8 个基差完整；同一 Parent 同时进入 B 的两种 cohort，断言折唯一键 `(regime,scenario,cohort,comparison,parent_article_id)` 不碰撞，训练数及预测独立。基差子集 M0/M1/M2 必须重估；M2 只配该子集 M1，不能取全量 M1 或改配 M0。
- [ ] RED：`test_summary_independent_error_contributions` 对独立误差向量 `error_M0=(1,2,3)`、`error_M1=(0,1,2)`，应得 `d=(1,3,5)`、mean=3；去掉各已算贡献后的均值为 4、3、2。对 `M2_vs_M1` 的 `error_M1=(0,1,2)`、`error_M2=(0,0,1)`，应得 `d=(0,1,3)`、mean=`4/3`。覆盖负增量、仅少量正贡献、并列、某折不可估；预期用这些常量手算，不调用生产 summary 造 oracle。正贡献按值降序、并列按 Parent ID 排序，只展示实际存在的最多三个；去掉贡献不重新训练，不称为重新拟合 Jackknife。
- [ ] GREEN：只实现 Design 的比较表：A/B/C 的 `oi_complete: M1_vs_M0`；B 的 `basis_complete: M1_vs_M0` 与 `M2_vs_M1`。每折按其 cohort 取训练数据，训练折内均值/总体标准差标准化，再构造唯一 `z_p*z_o`；`y` 不标准化，使用 `numpy.linalg.lstsq(rcond=None)`，列数和秩条件遵循 Design。不扩大模型、目标或特征。
- [ ] GREEN：每折记录基准/扩展模型、实际 y、两预测及误差、`d_i`、状态和训练 Parent 数；聚合按 `(regime,scenario,cohort,comparison)` 分开。任一预期折不可估时，该对完整集合增量为 null；仍保留各折状态，不用不同有效折数比较。报 MSE、绝对误差中位数、count/mean/median/min/max 的 y/MAE/MFE、Parent/日期集中度与贡献敏感性。空集正常报告证据不足，不把业务缺口当源文件错误。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py -k 'models or fold or cohort or summary'
```

记录独立数值 RED/GREEN；GREEN `RC=0`。测试浮点误差使用明确近似比较，不能将近零数值残差解释为经济改善；不引入新的晋级阈值。

## Task 3：真实入口接线、权限门禁与三份人工输出

**依赖：** Tasks 1–2。**文件：** SCRIPT、TEST。**不变量：** INV-01 至 INV-06。

**接口：** `main(argv: Sequence[str] | None = None) -> int`，CLI 仅接收 `--auth-file` 和 `--output-dir`。生产输入路径和两份快照 SHA 固定为 Design §2，模型不可从 CLI 调参；报告不解析旧 Markdown 数值。实际研究入口不导入旧 pipeline、真实上游 loader 或交易/网络客户端。

- [ ] RED：`test_cli_denies_before_snapshot_read` 验证无/坏授权、旧 Plan/Design 身份、缺字段、禁止权限不是严格布尔 false 时，入口在打开真实快照之前非零拒绝且不创建输出。实际执行者先核对用户原始授权；机器 JSON 本身不能证明用户同意，不得在缺少用户原始批准时自行生成“真实授权”，也不得将测试授权文件用于真实数据。
- [ ] GREEN：最小授权记录绑定 `operation=offline_research_once`、`design_relative_path/design_sha256`、`plan_relative_path/plan_sha256`、`input_csv_path/input_csv_sha256`、`input_review_path/input_review_sha256`、`output_dir` 和 `network_allowed/paper_trading_allowed/live_trading_allowed/execution_allowed/signal_allowed=false`。另用 `allowed_actions` 明确区分 `snapshot_validation` 与 `research_run`，它只能是这两个固定动作的非空、无重复子集；校验入口须有前者，CLI 完整研究须有后者，不能由一个动作推导另一个。源码中的获批 Plan SHA 由执行者从实际批准语句填入，不在本 Plan 内自引用推算；实际 Design/Plan 文件哈希也须匹配。路径解析后必须对应 Design 的精确输入和用户全新输出根，不接受旧任务授权。禁止无条件测试环境自动放权。
- [ ] RED：`test_cli_canonical_csv_to_all_outputs` 用 Task 1 canonical writer 夹具经过真正 `main`、loader、面板、模型与写出路径，检查三份文件、Parent 手算值、cohort 键、空/不可估比较、数值误差和报告标签。仅在测试进程 monkeypatch 固定输入路径/hash、批准身份为测试夹具，显式保留各校验分支；不提供生产 `--skip-auth`、`--input-hash` 或 `--synthetic` 绕过开关。这证明 canonical 格式兼容和入口接线，不证明真实快照运行已获授权。
- [ ] RED：`test_cli_output_isolation_and_partial_failure` 覆盖既有目录/文件、解析后的危险祖先/符号链接、输入文件或其目录被输出覆盖、执行中写出失败；检查输入 canary/hash 不变、RC 非零、无成功标志。坏 CSV 哈希应在建模前拒绝；元数据语义负向使用 Task 1 内部接口，不能为避开固定哈希放宽真实 CLI。
- [ ] GREEN：授权和路径检查通过后才校验两份输入实际 hash 并载入 CSV，再完成计算；排他创建输出目录及文件，不覆盖既有物。先写 `parent_panel.csv` 和 `fold_diagnostics.csv`，最后写 `review_CN.md`，仅在全部成功时将成功标志置于报告末尾并返回 0；失败留下的局部产物不能冒称完成，无需锁、fsync 或重启状态机。
- [ ] GREEN：面板列包含 Parent/机制/情景、全部 child 标识、所需及完整 child 数、主/基差资格、缺失与日期、p/o/b/y/MAE/MFE；折表按获批五元组唯一键记录；报告按 cohort 分组列出计数/交集、主 B 与 A/C 敏感性、基差补充、全部必要指标及贡献，并标明 `exploratory / historical_scenario_only / no_alpha_claim`、真实 PIT 未验证、LOPO 不是前瞻/未见样本。无正改善也属于可交付结果，不输出策略信号或自动 `alpha_candidate`。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py -k 'cli'
```

预期 GREEN `RC=0`，不得读取 `/private/tmp/launch_open_interest_basis_exploratory_run_20261103/` 的真实 bytes 来完成上述默认测试。独立上游 writer 仅负责夹具序列化，数值 oracle 仍是独立手算。

**另行授权后的门禁，不是实施默认任务：** 实现可被 `PRICE_OI_BASIS_SNAPSHOT_VALIDATION_AUTH_FILE` 显式指定的单次授权控制的 `test_authorized_exact_snapshot_contract`；环境变量缺失才以 `snapshot_validation_not_authorized` 明确 skip，给定文件但身份/动作不合法时失败，不能 skip 掩盖错误。该测试使用授权指定的真实路径核对 CSV/报告 SHA、Design §2 格式和状态映射，只做消费兼容检查、不拟合、不产生研究输出，不能无条件 skip 或将其当作已通过。Only-validation 授权运行完整 CLI 必须拒绝；研究许可也不默认授权该独立验证测试。只有用户另行授权实际完整运行，才可执行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py --auth-file "$AUTH_FILE" --output-dir "$OUTPUT_DIR"
```

`AUTH_FILE/OUTPUT_DIR` 只能来自适用用户批准记录，测试或执行者不得更改授权目录以继续；输入缺失/哈希变化则停，不重放 raw、不下载。实际运行记录 RC 与三输出 hash，并核对输入前后不变；RC=0 仅代表固定程序完成，不是发现 Alpha。

## Task 4：收尾与独立完成审计

**依赖：** Tasks 0–3 的代码与合成验证。**文件：** 无额外仓内文件。**不变量：** INV-01 至 INV-06。

- [ ] 执行完整新测试、Ruff、anti-shortcut scanner 和范围/空白检查，记录 actual process exit code，不能用测试摘要或 scanner clean 替代研究语义验证。只读核对 baseline 与 HEAD/staged/unstaged/untracked，保护起始已有文件；两个新路径是预期变化。记录候选代码 hash 与临时基线位置，不新建审计脚本。
- [ ] 分别报告“代码与合成入口完成”“授权后精确快照兼容验证”“实际研究运行”三个事实状态；后两项未授权时不执行，也不因未运行研究而要求改变已批准算法。执行者不能自行宣布 `complete`；交独立会话按本 Plan 范围审计。

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. .venv/bin/python -m pytest -q -p no:cacheprovider tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py
.venv/bin/ruff check --no-cache scripts/external_signal_shadow/run_launch_price_oi_basis_incremental_information.py tests/scripts/external_signal_shadow/test_run_launch_price_oi_basis_incremental_information.py
python3 .agent/tools/anti_shortcut_scan.py --base-sha "$BASE_SHA"
git diff --check "$BASE_SHA"
git diff --cached --check "$BASE_SHA"
git diff --cached --name-status "$BASE_SHA"
git status --short --untracked-files=all
```

测试/Ruff/scanner/diff-check 预期 `RC=0`，真实验证项的 skip 单列；还须直接阅读新建未跟踪文件并检查空白，不能靠 tracked diff 覆盖全部范围。此任务不改共享函数或图谱文件，不安排 Graphify 更新。

## 不变量到任务与机械证据

| Design 不变量 | 对应任务及证据 |
| --- | --- |
| INV-01 | 0、3、4：批准身份/基线、先授权后读取、固定快照 hash、输出隔离、禁止权限和范围核对。 |
| INV-02 | 1、2、3：canonical 字段、全部 child 的 Parent 资格、日期和缺口守恒、同 Parent 跨机制剔除。 |
| INV-03 | 1、2、3：不重选窗口、显式 A/B/C、训练标准化无留出泄漏、报告保持假设/PIT 边界。 |
| INV-04 | 2、3：独立仿射/交互/基差向量、Design 的 OLS 秩条件、同子集 M2 对 M1 增量及不可估处理。 |
| INV-05 | 2、3：双 cohort 唯一键、同样本重估、贡献敏感性、完整输出及非正结果不挑选。 |
| INV-06 | 1、3、4：canonical writer 正向、单点负向、真实 main 到三输出、独立 oracle 和实际 RC。 |

**Rule 16 路由：** 白名单内实现/测试缺口原地修复；需要额外路径但不改变语义时先停越界修改，申请有限 Plan 增补并核对受影响身份/证据；需要改变 Design 的模型、状态、输入快照、研究窗口或权限时 `BLOCKED_SPEC_DRIFT`，不得自行 fallback。Rule 17 仅使用结构检查及独立语义证据，不新增完整独立 verifier；旧 J-A/J-B/J-C 契约保持不动。

本 Plan 必须先经独立审查及用户正式实施批准。任何 `complete` 都只针对声明的实施范围，不授权 commit、push、部署、SSH、实际快照消费/研究运行或 paper/live/execution。
