# H1 S1 成交压力与价格减速：最小探索研究 Implementation Plan

日期：2026-11-20（Asia/Shanghai）

状态：`draft_not_approved`。Design 已获用户批准；本 Plan 尚待独立审查与用户实施批准。当前只起草本文件，不开始实施或真实数据运行。

绑定 Design：`docs/designs/2026-11-20-h1-s1-pressure-response-minimal-exploratory-research-design_CN.md`；SHA-256：`0e0a77ba15b31cc951f25bd471a981710ea52d63c0bd1f7275284ff73ed3de54`。

目标：只实现并验证一次 S1、M0/M1、唯一 X 的探索比较；交付可重算的有限资源判断，不建立策略、扫描器或正式 Stage。

## Allowed Change Scope

以下变量是精确路径的缩写，不是目录通配授权。`W` 必须原先不存在；不能碰撞后自动换目录或覆盖旧尝试。各 Task 的相关命令必须在同一 Bash 会话中运行，先执行本共用设置块；每个后续命令块也显式启用严格模式。另开 Bash 时只重载本设置块，不重新执行 Task 1 的建根/基线步骤。

```bash
set -euo pipefail
set -o noclobber
MAIN=/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
ISO=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/repo_2f9ba8e0
OLD=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/runner_pkg/run_h1_path_b_isolated_snapshot.py
PREFLIGHT=/private/tmp/h1-isolated-hist-2f9ba8e0-20261120/run_output_03/path_b_estimability_summary.json
PY=/Users/tanshuai/.local/share/uv/python/cpython-3.11.14-macos-aarch64-none/bin/python3.11
NPY="$MAIN/.venv/bin/python"
W=/private/tmp/h1-s1-minimal-experiment-20261120
DR="$W/read_h1_s1_experiment.py"
NF="$W/fit_h1_s1_experiment.py"
UT="$W/test_h1_s1_experiment.py"
DESIGN="$MAIN/docs/designs/2026-11-20-h1-s1-pressure-response-minimal-exploratory-research-design_CN.md"
PLAN="$MAIN/docs/plans/2026-11-20-h1-s1-pressure-response-minimal-exploratory-research-implementation-plan_CN.md"
BIND="$W/evidence/source_binding.json"
READ_OUT="$W/readout_01"
RESULT="$W/result_01"
OPERATION=H1_S1_MINIMAL_EXPLORATORY_20261120_01

# 仅记录一条命令的真实退出码；失败退出当前 Bash，禁止继续下游。
run_step() {
  local name="$1" rc
  shift
  local out="$W/evidence/$name"
  printf '%q ' "$@" > "$out.command"
  printf '\n' >> "$out.command"
  if "$@" > "$out" 2> "$out.stderr"; then
    rc=0
  else
    rc=$?
  fi
  printf '%s\n' "$rc" > "$out.rc"
  printf 'STEP=%s RC=%s\n' "$name" "$rc" >&2
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
}
```

| 类别 | 允许范围与条件 |
| --- | --- |
| Allowed implementation paths | 仅新建 `$DR`（只读历史读取与特征）、`$NF`（派生表验证与 NumPy 比较）；不修改旧脚本，不增加第三个生产模块 |
| Allowed verification paths | 仅新建 `$UT`；其内部使用标准库 `unittest` 的 `ReaderTests`、`NumericTests` 两个测试类；模块顶层仅标准库，各类延迟导入对应被测模块，ReaderTests 不依赖 NumPy，NumericTests 不导入读取器；临时合成文件限 `$W/test_tmp/` |
| Allowed documentation paths | 本 Plan 仅本轮起草；实施阶段冻结。Task 4 获授权后新建 `$RESULT/review_CN.md`，不回写已有讨论、Design 或预审报告 |
| Allowed generated/runtime artifacts | `$W/evidence/` 下的基线、RED/GREEN、门禁、运行日志、身份记录与 source binding；Task 4 才允许创建 `$READ_OUT/features.json` 和 `$RESULT/{predictions.json,parent_loss.json,summary.json,review_CN.md}`；不生成其他数据结果 |
| Affected but unchanged | `$OLD`、`$ISO` 的全部源码/配置/上游原件、主仓代码/配置、`$PREFLIGHT`、旧三次授权与输出；以 SHA、双 HEAD、模块来源、公开 loader 及前后工作区快照核验；数值进程不得消费历史根 |
| Forbidden | 白名单外修改，读取 J-B 收据/其他研究结果作输入，联网/下载/依赖安装，配置/冻结哈希更新，D/F/Producer/VPS 操作，交易与成本后优势声明；禁止 `ruff check --fix .`、`git clean -fdx`、自动 add/commit/push、原地覆盖或自行增加实验/重跑 |

本轮只新增 Plan；将来获批的 Tasks 1–3 只允许代码、合成测试及已暴露预审汇总的名单/身份核对，不允许打开 J-A 原始正文、ZIP 或分类账本。Task 4 的真实读取及拟合必须另获新批准，不能通过把旧授权中的 false 改成 true 取得权限。

## 1. 冻结身份、复用与预算

### 1.1 身份核对

- 主仓 `HEAD=7bdb29bfc89155d6b155df6bed61479a496d3da9`；隔离根 `HEAD=2f9ba8e04821c3d7a477a65f2b73e34cb6beb442`。任一变化即停止，不能以“只是提交了文档”自动豁免。
- `$OLD` SHA-256：`6b78a3f1c32d771cd767e599c34175b125a1248e226f84fbc1d8304cab879959`；`$PREFLIGHT`：`bf1fdb3e93c57de008c1612bacafec51ef57f735e654f2688fd9082366fed6cd`。
- 预审人工报告 `docs/reviews/2026-11-19-h1-trade-pressure-response-estimability-preflight_CN.md` SHA-256：`14685695e159629884df74ac001932fbace24eda0a6d2e6a60a4a4ce3a24795e`。
- `$PY` 为 `Python 3.11.14`，实际二进制 SHA-256：`6d95b60cb17e9644ddcbdb4dd4797e7e93e7e75f8ad0c09f95b5967ef8c19e5e`。历史读取禁止主仓 venv；`$NPY` 为 `Python 3.11.14 + NumPy 2.4.6`，仅用于数值进程与合成数值测试。
- Plan 自身 SHA 在获批时由实际文件计算；不在本文件内嵌自身摘要。保存批准原文，并要求它绑定实际 Plan/Design，不把审查推荐当授权。

`JA=$ISO/data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z`。下表固定其余路径；`$JA/`、`$ISO/` 均展开为以上根，不使用 latest 查找。最后一列完整 SHA-256 来自未修改的 `$OLD.FROZEN_ISOLATED_PATH_B_FILE_HASHES`。

| 文件 | SHA-256 |
| --- | --- |
| `$JA/manifest.json` | `b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf` |
| `$JA/summary.json` | `722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b` |
| `$JA/request_journal.jsonl` | `b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa` |
| `$JA/review_CN.md` | `1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152` |
| `$ISO/.git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json` | `c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b` |
| 上一文件完整路径加 `.sha256` | `70948a929538ac32928e8032de5a7c9ac1e35b5af462486ea9b7ca3f2f120649` |
| `$ISO/.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/network_authorization.txt` | `3a4c31cb12e6a16e9b9a8afc0a8169761d276f6bd17568481bbad20577a298fe` |
| `$ISO/.git/plan-execution/stage1_5j_a/b578ab6b82ffcf36ff3f9bcefd3cb4989bf1be9cf64ae70d09fddfcbb2f76a82/network_authorization.sha256` | `35fae05065c0d49ee122756455069f8e24a80f665fdf192ea44e7b42b1f9f5b0` |
| `$ISO/data/exports/stage1_5j_token_launch_classification_ledger_v2.csv` | `36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b` |
| `$ISO/configs/base.py` | `473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc` |
| `$ISO/configs/stage1_5j_b_historical_aggtrades_launch_response.py` | `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4` |
| `$ISO/src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py` | `250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18` |
| `$ISO/src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py` | `7e0e696647acf158facbdd8d3d39351bbc68c33b039871f26f4a38bc75ad56e5` |
| `$ISO/src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` | `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f` |
| `$ISO/src/research/external_signal_shadow/launch_taker_buy_share_residual_response.py` | `ef126ceb83f978f231271a39b091b670ae2e7e7054021230ac3edad29b9a41df` |
| `$ISO/src/research/external_signal_shadow/launch_open_interest_basis_exploratory.py` | `ed9d68767d56f884f13b02cb5d323a602b8595518dc4c108577ee9092f5426be` |

以上上游数据文件的实际读取/校验安排在 Task 4；Tasks 1–3 仅检查源码、现成汇总、解释器和路径，不提前调用 loader。J-A strict loader 附带的全根检查必须如实记录，不能宣称只读了 51 份 ZIP。历史 network authorization 仅证明来源，不赋予本次联网权限。

### 1.2 主要复用承诺

| 已有能力 | 实际调用位置 / 适配边界 |
| --- | --- |
| `$OLD.load_isolated_runtime_dependencies`、`verify_module_origins_isolated` | `$DR` 的真实读取入口；仍复核冻结 parser 的实际 origin，禁止从主仓导入历史模块 |
| `$OLD.verify_static_isolated_path_b_identities`、`verify_dual_git_heads` | Task 4 前后核验；前者不代替公开 strict loader，后者参数用本 Plan 双 HEAD |
| `load_verified_stage1_5j_a_historical_archive_coverage_root`、`build_admitted_ja_context` | `$DR` 准入入口；从 J-A 真实加载，不以预审 JSON 或手造 summary 替代 |
| `$OLD.reconcile_v2_ledger_against_ja_summary` | `$DR` 重证账本/正文 AST，取得 53/42 名单，再按已批准上游缺口规则保留 51/41；不接触 J-B 收据 |
| `$OLD._iter_admitted_packages_trades` | 复用其对 `open_verified_package_stream`、`stream_aggtrades_csv_lines`、header 和日期包的实际调用；私有函数接口仅作冻结版本内局部复用，不创建通用包装 |
| `required_utc_dates_for_window`、`$OLD.select_anchor_via_canonical_helper` | 依次取实际所需日期包及原锚点；300,000ms 规则保持不变；不得改用纯预审 T0 跳过重证 |
| `$OLD.FeatureSubwindowAccumulator` | W1/W2 的精确买卖成交额；新增边界价格与 y 累积。不复用旧 `evaluate_child_window_stream`，因为其禁止读未来价格且缺少本实验端点；不修改旧函数 |

只导入不调用不算履约；Task 4 日志、调用链和输出记录必须能定位实际调用。新增计算只限端点、冻结特征、OLS/分组/汇总；不复制整份旧脚本，不强行引入 J-B receipt loader。

### 1.3 新预算提议（待用户确认）

建议新增总上限 **4.00 小时累计工作投入**：Task 1 分配 1.00h，Task 2 1.50h，Task 3 0.50h，Task 4 与独立审计/报告合计 1.00h。Plan 独立审查也计入本次总额，从 Task 3 分配中扣除；若评审超过分配，可在总额内透明调整，不自动追加总额。

这是基于复用冻结读取链、已有 NumPy、仅一个交互和一次真实运行提出的资源封顶，**不是实测工期或完成承诺**。记录实际开始/结束与工具运行时间；人工/外部审查无法准确计量时标明估算并按保守上界扣减。旧预审 4h 已结项，不挪用余额、不重置。获批实施前用户须明确接受此预算；达到上限仅交付已完成项和缺口，不为了跑出结果继续开发。

## 2. 输出边界与共用验证约定

### 2.1 最小派生表与结果

`features.json` 是本次读取进程到数值进程的唯一数据表，允许同时保存以下必要诊断；不得隐式读取其他研究结果补列。

| 内容 | 必填语义与校验 |
| --- | --- |
| 身份头 | operation、Design/Plan/source binding SHA、双 HEAD、预审 SHA、真实输入与模块 origin、解释器/源码身份；读者/消费者明确匹配 |
| 名单与分母 | 冻结预审 S1 的完整 53 个 `(parent_article_id,symbol)`、42 Parent、两条已知缺口及 51/41 计算名单；唯一键、父子映射、差集均须守恒 |
| 每个计算 child | 官方时间、重证 T0/D/E、W1/W2 精确 A/B/V 与 s、全部边界价格、实际时间/ID/年龄、r1/r2/d/R/Z/S/X/RV/L/H、y、零 sequence gap 证据 |
| RV 证据 | 5m 至 25m 的 21 个 `P(b-)` 引用与 20 个分钟收益；每个价格位于其左侧一分钟；非有限值拒绝 |
| 分组 | Parent、D 所在 UTC 日；数值进程独立重建块，不信任生产者预先写出的 fold 或预测 |

金额用既有 Fraction 精确累积并保存分数文本；特征/收益用 float64 可表示的有限数。不得把 Fraction 文本先转近似值再判断 s 是否严格大于 0。JSON 禁止 NaN/Infinity；空集合/不适用值只能按已声明语义使用 null，不用必填字段 `.get(...,0)` 掩盖缺口。

`predictions.json` 保存训练/评价成员、权重、标准化参数、秩/奇异值/条件数、原尺度系数、预测与真实标签；`parent_loss.json` 保存 child→Parent 归约、Parent/块固定贡献逐一剔除；`summary.json` 保存全部分母、真实状态、主要/次要指标和权限边界。只在对应步骤完整结束后写该步骤的最终 JSON；失败非零并留日志，不能让部分结果冒充完成。不为单写者可重算文件新增锁、封树或崩溃恢复框架。

### 2.2 权限与运行方式

- `$DR` 导入旧脚本时仅取定义/常量，不调用旧授权 verifier 或旧 `run_authorized_isolated_path_b_preflight`；新真实消费由新批准原文与 source binding 限定。
- `$NF` 只导入标准库与 NumPy；不导入 `$DR`、`$OLD`、`configs`、`research`、`src`，不打开历史树或归档。运行前后记录 NumPy 版本与真实 origin；不得借测试运行读取实源。
- 真实入口对控制 GO/STOP 的条件使用显式异常/条件分支，不用可被 `-O` 删除的 Python `assert`。可用窄 audit hook 拒绝 socket 行为和对已知输入根的写入/数值进程读取；这不是完整 OS 沙箱证明，不新增安全框架。
- 每步保存完整命令、真实 RC 和独立 stdout/stderr；所有执行块保持 `set -euo pipefail` 与 `noclobber`，通过上面的内联 `run_step` 逐条执行，不新增运行脚本或调度器。仅包装下文的单条外部命令或 `test`，不得将 `run_step` 放进 `if`、`!`、`||` 等忽略失败的调用上下文，也不得用 `set +e` 放行主体门禁。首次 W 检查/建根失败时尚不能写证据根，须向调用者 stderr 报 RC 并非零退出；其余步骤保存 `$name`、`$name.stderr`、`$name.command`、`$name.rc`。记录失败或日志路径碰撞本身也终止，不能用末条成功、`tee` 或重写日志掩盖失败。未预期 skip/xfail、空测试选择集或新增失败均停止。

## 3. Task 1 — 可核验的 S1 读取与端点切片

**依赖：**Plan 独立审查、用户实施批准及预算确认。对应 `INV-01/02/03/04/08`。只新建 `$DR`、`$UT` 的 `ReaderTests` 与 evidence/test_tmp；本 Task 不调用真实 loader。

### 3.1 执行前基线

先核对批准原文、Design/Plan SHA 与双 HEAD。预先确认 W 不存在后，才创建 `W/evidence`、`W/test_tmp`；保存以下证据，不改 Git index，不清理用户已有变更。

```bash
set -euo pipefail
set -o noclobber
if [ -e "$W" ] || [ -L "$W" ]; then
  printf 'STOP=work_dir_exists RC=1\n' >&2
  exit 1
fi
mkdir "$W" || { rc=$?; printf 'STOP=work_dir_create RC=%s\n' "$rc" >&2; exit "$rc"; }
mkdir "$W/evidence" "$W/test_tmp" || { rc=$?; printf 'STOP=evidence_dir_create RC=%s\n' "$rc" >&2; exit "$rc"; }
run_step BASE_SHA git -C "$MAIN" -c core.fsmonitor=false rev-parse HEAD
run_step before.status git -C "$MAIN" -c core.fsmonitor=false status --short --untracked-files=all
run_step before.worktree.patch git -C "$MAIN" -c core.fsmonitor=false diff --binary
run_step before.index.patch git -C "$MAIN" -c core.fsmonitor=false diff --cached --binary
run_step before.untracked git -C "$MAIN" -c core.fsmonitor=false ls-files --others --exclude-standard
run_step bound.sha256 shasum -a 256 "$DESIGN" "$PLAN" "$OLD" "$PREFLIGHT" "$PY"
```

补存 before.status 中所有既有修改/未跟踪文件的 SHA，尤其 Design、预审、讨论备忘与理论议程。执行后比较这些实际字节，不能仅以主仓 diff 不含本次代码证明无越界。基线若与 §1.1 不符，在修改代码前停止。

### 3.2 RED → GREEN：真实行为边界先行

`$DR` 提供 `reduce_s1_child(trades, *, parent_article_id, symbol, symbol_launch_time_ms, deps) -> dict`，输入按既有七列交易映射流式消费，输出 §2.1 的一个 child；无单独的可配置窗口。公开 `main(argv=None) -> int` 承担 source binding / 环境 / 真实准入，不能通过纯函数单测冒充 CLI 接线已通过。

- [ ] 先写 `ReaderTests` 的端点、方向、序列及隔离失败用例；为导入建立最小模块骨架后取得行为不符合预期的 RED，不能把语法错误、找不到路径或解释器错误算业务 RED。
- [ ] 独立向量：T0=0，端点价格 P5-=100、P15-=90、PD-=90、PE=99；预期 r1=ln(0.9)、r2=0、d=−ln(0.9)、y=ln(1.1)。W1 的 A/B=75/25，W2=60/40，预期 s1=1/2、s2=1/5、R=S=1、Z=X=d。金额与端点可分别测试，避免为一个向量手工伪造完整 J-A 来源。
- [ ] `test_boundary_prices_and_direction`：边界恰好 5m/15m/D 的成交不作该 `P(b-)`，但按半开区间计入新窗口；恰好 E 的成交可作标签。相同毫秒不同 ID 必须取物理最后一笔；重复/倒序 ID、倒序时间、窗口内 ID 缺口拒绝。
- [ ] `test_future_prices_do_not_change_features`：仅改 `[D,E]` 价格或 E 以后的成交，所有特征不变；改标签端点可以只改变 y；E 后成交不能成为结果价格。非有限/非正价格、零 V、缺少任何必需分钟端点或额外计算名单缺口必须停止，不删 child。
- [ ] `test_environment_and_input_guards`：`--check-environment` 只检查解释器、源码/模块 origin 及禁止 import，不调用 loader/归档读取。源路径/摘要错误、主仓历史模块污染、普通网络调用均显式失败；调用哨兵证明 loader 未被执行。
- [ ] 最小实现按 §1.2 接线；依次定位重证锚点、S1 日期包、21 个分钟边界及 E 端点。只把 D 前价格送入特征，D 后只维护标签端点/必要覆盖，不计算未来 MAE/MFE 或完整价格路径。不把旧预审 evaluate 函数改开关复用。

验证：以下为 GREEN 命令，RC 均须为 0，真实执行全部 `ReaderTests`、无 skip。预期非零的 RED 在独立 Bash 会话中使用独立 red 日志名执行，由调用者核对真实非零 RC 与失败原因后再开始修复；不能在主体成功依赖链中忽略该失败或覆盖日志。

```bash
set -euo pipefail
set -o noclobber
cd "$W"
run_step task1.reader.green.log env -u PYTHONPATH -u PYTHONHOME -u GIT_DIR -u GIT_WORK_TREE PYTHONDONTWRITEBYTECODE=1 "$PY" -B -m unittest -v test_h1_s1_experiment.ReaderTests
run_step task1.reader.optimized.green.log env -u PYTHONPATH -u PYTHONHOME -u GIT_DIR -u GIT_WORK_TREE PYTHONDONTWRITEBYTECODE=1 "$PY" -O -B -m unittest -v test_h1_s1_experiment.ReaderTests
```

## 4. Task 2 — 同样本 M0/M1 与资源判断切片

**依赖：**Task 1 合成门禁通过。对应 `INV-02/03/04/05/06/07`。仅新建 `$NF`、扩展 `$UT.NumericTests`；不读取实源、不调用读取进程。

### 4.1 固定实现接口与数值路径

`$NF` 提供 `evaluate_s1_rows(rows) -> dict`（纯计算，返回预测/损失/汇总）、内部 `fit_weighted_ols(design, y, weights) -> dict`、`main(argv=None) -> int`（只消费已绑定的 features 表）。测试不要求为了 mock 新建接口层。读取器输出的原始字段由数值入口重算/验证，不能直接信任已填好的 X、y、分组或样本计数。

```text
M0_COLUMNS = (intercept,r2,d,R,Z,s1,s2,S,RV,L,H)
M1_COLUMNS = M0_COLUMNS + (X,)
R=1[r1<0]; Z=R*d; S=1[s1>0 and s2>0 and r1<0]; X=S*d
w_child = 1 / (n_training_parents * n_children_of_its_parent)
A = sqrt(w)[:,None] * standardized_design; b = sqrt(w) * y
U,s,Vh = numpy.linalg.svd(A, full_matrices=False)
cutoff = numpy.finfo(numpy.float64).eps * max(A.shape) * s[0]
full_rank = count(s > cutoff) == number_of_columns
beta_std = Vh.T @ ((U.T @ b) / s)  # 仅在 full_rank 后求解
```

- 共通连续列用相同训练数据/权重计算同一 mu/sd；R/S 不标准化，截距不变，y 不标准化；训练 sd=0、非有限或 SVD 不收敛均按 Design 停止。原尺度系数 `beta_raw_k=beta_std_k/sd_k`，原截距扣除各 `beta_raw_k*mu_k`；二元列不作换算。
- 按 Parent 与共享 D 的 UTC 日做局部连通合并；排序键为块最早 D，同时间以稳定 Parent ID 排序。训练只含更早块且该 Parent 全部 E<评价块最早 D；Parent 不拆分，当前块不得贡献标准化或训练标签。
- 从最早满足训练 Parent>12、非截距列非恒定、M0/M1 满秩且 X 新增一维的块开始。起点仅依赖特征/身份/时间；之前为 warmup。开始后秩或数值失败非零停止，不能跳块。始终没有合格起点是合法 `evidence_insufficient` 输出（RC=0、n_eval=0、比较指标 null），不是研究正结果。
- 使用 `numpy.errstate(over='raise',divide='raise',invalid='raise')` 配合显式有限性检查；预测、原尺度系数、误差平方、损失或汇总非有限时均非零，不生成成功 summary。条件数只披露，不自创新阈值、Ridge 或极值裁剪。
- 唯一主要指标为 Parent 等权 Delta；报告 MSE/RMSE/G、逐 Parent 绝对误差、y/delta 分布与极端预测。Parent 和块逐一剔除只从固定贡献重算剩余均值，不重新拟合；系数中位数按每块一次。严格沿 Design §5 分流，Alpha `research_status=evidence_insufficient`，`minimum_economically_meaningful_gain=null`。

### 4.2 独立期望与 RED → GREEN

- [ ] `test_weighted_standardization_and_ols`：Parent A 两个 child，Parent B 一个 child，x=(0,2,4)，y=(1,3,5)，w=(1/4,1/4,1/2)；手算 mu=2.5、sd²=2.75、原截距/斜率=1/1，x=6 预测=7。低维向量只验证求解器，不豁免真实 M0/M1 的列数/样本保护。
- [ ] `test_rank_gate_and_warmup`：给定带截距的一组线性独立基向量，应增加一列恰多一秩；令 X=Z 或某必需列为常数时拒绝。13 个 Parent、同 Parent 多 child、12 个 Parent及“开始评价后才退化”的四种情况分别覆盖；不能用 child 数替代 Parent 数。
- [ ] `test_parent_and_day_pit`：同 Parent 跨 UTC 日时连同两日其他 Parent 合并；某 Parent 最后一条 E 等于测试最早 D 时不得训练；未来特征变化不改变过去预测，改变测试块 y 不改变其预测；仅改有限 y 不改变 warmup、名单、分组。
- [ ] `test_parent_loss_and_fixed_deletion`：A 的 y=(1,3)、M0=(0,4)、M1=(1,2)，B 的 y=5、M0=4、M1=3；手算 L0_A=L0_B=1，L1_A=1/2、L1_B=4，delta_A=1/2、delta_B=−3，Delta=−1.25、MSE0=1、MSE1=2.25、G=−1.25；固定剔除 A 剩−3，剔除 B 剩1/2，不调用拟合。补单 Parent/单块剔除后 null、MSE0=0 时 G=null 的边界。
- [ ] `test_outcome_routing_and_nonfinite_stop`：分别给出 Design §5 每个分支；正 Delta 但系数中位数非正、任一删除非正/null 不得晋级；非有限输入/预测/损失与注入 SVD 不收敛必须非成功，不借全绿测试掩盖失败。
- [ ] `test_numeric_process_has_no_archive_access`：监测真实 CLI 的 import/open/socket，禁止读取器、历史根、账本及归档访问；特征表摘要、名单、字段或代数不符即拒绝。正向表来自本次特征 writer，不手工制造“J-A 已验真”的 provenance；真正 J-A 兼容只由 Task 4 证明。

验证：RED 与 GREEN 分开会话/日志，按 §3.2 核对预期失败，不放宽主体门禁；以下两条 GREEN 应 RC=0、所有 NumericTests 真执行、无 skip，NumPy 版本及 origin 必须符合绑定。

```bash
set -euo pipefail
set -o noclobber
cd "$W"
run_step task2.numeric.green.log env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 "$NPY" -B -m unittest -v test_h1_s1_experiment.NumericTests
run_step task2.numeric.optimized.green.log env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 "$NPY" -O -B -m unittest -v test_h1_s1_experiment.NumericTests
```

## 5. Task 3 — 只读运行包与合成验证交付

**依赖：**Tasks 1–2 通过。对应 `INV-01/04/07/08`。只写 `$W/evidence`，必要修复仍限原三文件；无实源测试，无新增 verifier/运行框架。

- [ ] 保存全部 RED/GREEN 命令、时间、RC、测试选择/执行数。补测既有输出碰撞时拒绝且旧字节不变；不得以缺实源而 skip 合成必过项。在 `ReaderTests` 加入 `test_shell_fail_stop`：抽取本 Plan 的实际 Bash 块，共用设置后只将变量/可执行程序绑定到 `$W/test_tmp` 的合成路径；分别注入 W 已存在、DR 写出合成表后 RC=1、shasum 非零、NF 非零。四者整段 RC 均非零；后续哨兵不得执行，已存文件字节不变，失败步骤 RC 保留。另保留全成功对照，防止空跑/无条件停止冒充正确；不得改写成另一条简化控制链代替被测命令。
- [ ] 形成 `$BIND`：机器可读的**待批准输入/代码清单**，记录 operation、双 HEAD、Design/Plan/PREFLIGHT/OLD SHA、三份新源码的 SHA、解释器/NumPy 身份、§1.1 的 16 项路径/摘要、从冻结预审提取的 S1 全名单/缺口/分母、精确新 readout/result 路径和禁止动作。字段要求由此清单限定，不复用旧 27 键授权 schema，不填已获准的虚假布尔值。文件本身不是授权证书，执行者必须另核验用户批准原文；改变清单须重新审查受影响绑定。
- [ ] `$DR --check-environment` 与数值环境预检在调用任何真实 loader 前完成；固定 Python/NumPy 导入来源，记录 main/isolation 前后 HEAD 与代码来源。真实读取入口核对 source binding 字节、operation、脚本及输入身份，不仅比较传入摘要字符串。
- [ ] 运行以下静态门禁并保存真实 RC。scanner 必须显式传入仓外两个生产文件并使用 `--all-lines`；空主仓 diff 不是扫描它们的证据。Tests 不强制接受生产 scanner 的伪来源规则。

```bash
set -euo pipefail
set -o noclobber
run_step task3.ruff.log "$MAIN/.venv/bin/ruff" check --no-cache "$DR" "$NF" "$UT"
run_step task3.scanner.log env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$MAIN/.agent/tools/anti_shortcut_scan.py" --all-lines "$DR" "$NF"
run_step task3.bound.log shasum -a 256 -c "$W/evidence/bound.sha256"
run_step task3.diff-check.log git -C "$MAIN" -c core.fsmonitor=false diff --check
run_step task3.index-check.log git -C "$MAIN" -c core.fsmonitor=false diff --cached --check
run_step after_implementation.status git -C "$MAIN" -c core.fsmonitor=false status --short --untracked-files=all
run_step after_implementation.worktree.patch git -C "$MAIN" -c core.fsmonitor=false diff --binary
run_step after_implementation.index.patch git -C "$MAIN" -c core.fsmonitor=false diff --cached --binary
run_step task3.status-cmp.log cmp "$W/evidence/before.status" "$W/evidence/after_implementation.status"
run_step task3.worktree-cmp.log cmp "$W/evidence/before.worktree.patch" "$W/evidence/after_implementation.worktree.patch"
run_step task3.index-cmp.log cmp "$W/evidence/before.index.patch" "$W/evidence/after_implementation.index.patch"
run_step task3.readout-absent.log test ! -e "$READ_OUT"
run_step task3.result-absent.log test ! -e "$RESULT"
```

同时复核既有修改/未跟踪文件摘要与安全配置 `RISK_LIVE_TRADING_ENABLED=False`、Producer=False；禁止通过修改配置让历史 loader 通过。三份新源码哈希和 BIND 哈希交用户核对；到此只能报告“合成验证交付”，不能宣称真实数据已验证或全部研究 complete。

## 6. Task 4 — 单独授权后，一次真实读取 → 拟合 → 独立审计

**依赖：**Tasks 1–3 的证据可核验；用户另行批准精确 `$BIND` SHA、新 operation、读取范围及两个全新输出目录，且确认剩余预算。对应全部 `INV-*`。用户仅批准本 Plan 的 implementation，不自动满足这个条件。

### 6.1 前检与一次执行

- [ ] 将真实批准原文保存在 `$W/evidence/run_approval.txt`；不能把推荐审查或旧 `_03` 批准改名充当新授权。实际 BIND SHA 赋给 `BIND_SHA`，其值必须与用户批准逐字匹配，不是随取当前值就自动获得权限。
- [ ] 重核主仓/隔离 HEAD、Design/Plan/源码/解释器/NumPy、source binding、16 项上游实际字节和侧文件；J-A profile 原有语义/封树检查继续由公开 strict loader 承担。不新增本实验的 full Rule 17 profile，也不直接把旧闭环 receipt 复制成新证书。
- [ ] 确认 READ_OUT/RESULT 均不存在；先环境预检，再按以下顺序真实调用一次。变量已于顶部固定；每条分别保存日志/RC，前一步非零则不执行下一步。`FEATURES_SHA` 是本次成功读取后实际特征表摘要，必须记录并与数值入口实际字节核对。

```bash
set -euo pipefail
set -o noclobber
: "${BIND_SHA:?STOP=approved_binding_sha_required}"
cd "$W"
run_step task4.readout-absent.log test ! -e "$READ_OUT"
run_step task4.result-absent.log test ! -e "$RESULT"
run_step task4.environment.log env -u PYTHONPATH -u PYTHONHOME -u GIT_DIR -u GIT_WORK_TREE PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B "$DR" --check-environment --source-binding "$BIND" --source-binding-sha256 "$BIND_SHA"
run_step task4.reader.log env -u PYTHONPATH -u PYTHONHOME -u GIT_DIR -u GIT_WORK_TREE PYTHONDONTWRITEBYTECODE=1 \
  "$PY" -B "$DR" --source-binding "$BIND" --source-binding-sha256 "$BIND_SHA" --output-dir "$READ_OUT"
run_step task4.features.sha256 shasum -a 256 "$READ_OUT/features.json"
read -r FEATURES_SHA SHA_FILE < "$W/evidence/task4.features.sha256"
[[ "$FEATURES_SHA" =~ ^[0-9a-f]{64}$ ]] || { printf 'STOP=invalid_feature_sha RC=1\n' >&2; exit 1; }
run_step task4.numeric.log env -u PYTHONPATH -u PYTHONHOME PYTHONDONTWRITEBYTECODE=1 \
  "$NPY" -B "$NF" --source-binding "$BIND" --source-binding-sha256 "$BIND_SHA" \
  --features "$READ_OUT/features.json" --features-sha256 "$FEATURES_SHA" --output-dir "$RESULT"
```

真实读取必须保存 strict loader、AST 对账、53/42→51/41 完整差集、端点/分钟新要求、模块 origin 和实际读取范围。任何新增缺口、身份不符或真实入口不兼容均停止，不能补数据、排除失败 child、绕过 loader 或自动第二次运行。局部返修/新授权是否需要重跑按 Rule 16 与已改变的绑定判断，不能以“参数没变”继承旧源码证据。

### 6.2 独立语义复核与结果报告

- [ ] 独立审计者只读核验 source binding、运行批准、全部 RC 与前后快照。复核结构/名单守恒；不调用生产汇总函数，使用独立算式从预测表重新计算每个 Parent 的 L0/L1/delta、Delta、G 和固定贡献剔除。报告最大偏差及浮点精度说明；比较容差不得作为研究晋级阈值。
- [ ] 检查全部 fold 的训练/评价 Parent 不交叉、标签终点严格早于评价最早 D、权重每 Parent 相同、标准化只用训练数据、M0/M1 共通列一致。重算特征代数与端点顺序，并通过合成向量验证其定义；不是使用同一 reducer 再跑一次自证。
- [ ] 所有错误/无可识别起点/无增量/脆弱增量/有限正增量按 Design 分开陈述；展示 warmup 和真实评价分母，不将 41 Parent 都称样本外。报告 y/误差/delta 全部观测与尾部，不以另一指标替换 Delta；无评价样本时所有比较量 null、说明缺口，不制造零值。
- [ ] 新建 `$RESULT/review_CN.md`，包含问题、实际身份/命令/RC、数据/密度/结构/执行成本各层结论、预算实际消耗及下一步。执行成本、可成交性、容量和交易尾损仍为 N/A/未验证；不报告利润、因果或实时可用性。输入及主仓字节前后不变性、结果文件 SHA 留在 evidence。
- [ ] 执行者交付结果及缺口，不自审宣布 complete。独立 Completion Audit 在回复中给出 `complete/incomplete/blocked`；`complete` 只代表当前批准范围已验证，或已按契约诚实交付证据不足，不代表发现 Alpha、恢复 D2 或授予任何交易/运行权限。

## 7. INV → 任务与门禁矩阵

| Design 不变量 | 实施任务 | 必须核验的命令/证据 |
| --- | --- | --- |
| INV-01 身份与权限 | 1、3、4 | 双 HEAD / bound.sha256 / source binding 与实际批准；ReaderTests 环境负例；实际 loader/origin；前后快照 |
| INV-02 名单与计权 | 1、2、4 | ReaderTests；NumericTests 的 parent/day/PIT 与权重向量；真实 53/42→51/41、warmup/eval 守恒 |
| INV-03 PIT 与端点 | 1、2、4 | ReaderTests 边界/未来隔离；NumericTests 时间分组/标签隔离；真实端点与 train E<test D |
| INV-04 单候选 | 1、2、3 | 固定列顺序/特征代数；源码检查；无窗口/阈值/模型搜索；source binding |
| INV-05 可识别性 | 2、4 | NumericTests 秩/warmup/非有限反例；SVD 容差及各折矩阵诊断；无降基准兜底 |
| INV-06 公平比较 | 2、4 | NumericTests WLS 与手算损失；真实权重/标准化/预测重算；Delta 唯一主指标 |
| INV-07 证据诚实 | 2、3、4 | NumericTests 分流/null/固定删除；无 skip 冒充实源；summary/review 的受限声明 |
| INV-08 最小化与停止 | 1、3、4 | 复用调用链；显式仓外 scanner/ruff；代码/工作区不变性；预算/一次运行日志；无新框架 |

## 8. 失败路由、验收与权限

局部代码/测试偏离已批准定义且能在三文件内修复，按 `BLOCKED_IMPLEMENTATION_DEFECT` 修复与定向回归；仅需新增文件/任务且不改语义，先 `BLOCKED_SCOPE_DRIFT` 停止并提有限 Plan 增补；必须改变窗口、端点、名单、模型/损失、权限或冻结上游时 `BLOCKED_SPEC_DRIFT`，退回 Design/Plan。不得用“最小化”消除必要验证，也不得借审计重构无关代码。

本 Plan 不把 51/41 的新端点合格或 SVD 可拟合当作既成事实，不保证有评价样本或正向 Delta。有限结果可以完成预定问题；资料/预算不足不能伪称 H1 科学证伪。新增输出仅供本次数值消费及人工复核，不授予后续自动准入。

**当前待办：**独立 Plan review → 用户精确 SHA 实施批准并确认新增预算 → Tasks 1–3 → 用户按新 BIND 单独批准 Task 4 → 一次真实运行与独立 Completion Audit。无逐 Task 自动 Git 提交，不启动 SSH、VPS、采集启停、Producer、paper/live/execution。
