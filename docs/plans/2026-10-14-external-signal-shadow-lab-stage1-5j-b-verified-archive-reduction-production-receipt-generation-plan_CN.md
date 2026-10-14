# Stage 1.5J-B Verified Archive Reduction Production Receipt Generation And Closure Audit Implementation Plan

> **For executor:** 仅在用户外部批准本 Plan 后，才可按 `.agent/workflows/execute-approved-plan.md` 逐 Task 执行。本 Plan 授权单次正式生成 Stage 1.5J-B 生产回执并进行独立双重闭环收敛审计。严禁 commit、push、deployment、SSH、网络请求、consumer 消费、replay 模拟、信号生成、模拟盘或实盘交易。

**状态:** `draft_for_user_approval`  
**日期:** 2026-10-14  
**Planning BASE_SHA:** `1d445a23e9a742841d80b0997798caba530e8a94` (Commit of verified streaming reduction remediation)  
**目标 RUN_ID:** `stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z`  
**目标 Receipt 相对路径:** `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z`  

---

## 0. 绑定权威设计与契约矩阵 (Binding Authorities)

| 权威文件 | 相对路径 | SHA-256 | 约束管辖范围 |
| :--- | :--- | :--- | :--- |
| **Parent J-B Design** | `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md` | `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b` | 基础价格响应探索性问题定义、5m/1h/4h 窗口与中位数归约 |
| **Rebind Delta** | `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md` | `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c` | 上游 J-A replacement root 绑定、4 个文件摘要与 335/131/125/120/11/281 投影基准 |
| **Compatibility Domain Delta** | `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md` | `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f` | 阶段配置路径、9 个离线不可变常量与单次生产授权凭证结构 |
| **Governance Rule 17 v2 Delta** | `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md` | `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454` | 独立 `stage1_5j_b_receipt_v2` 结构验证器及封闭树校验规则 |
| **Remediation Design Delta** | `docs/designs/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-design-delta_CN.md` | `7e305093027de1d7c9f3d3221aaa237def317c4033e4bed3e837697fe94c0a9d` | 流式归约缺陷修复（INV-JB-RR-01 ~ 05）及 Legacy Roots 废弃标记 |
| **Approved Remediation Plan** | `docs/plans/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-implementation-plan_CN.md` | `1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd` | 生产凭证所绑定的执行实施方案 SHA |

---

## 1. 目标与执行边界 (Goal and Scope Boundaries)

**目标:**  
使用已提交固化（commit: `1d445a2`）的 Stage 1.5J-B 生产流式归约引擎，在完全离线、内存受控（单包单块 65536 字节缓冲上限）、无网络访问的条件下，对上游 J-A 准入的 280 个成交归档 ZIP 执行确定性全量处理，生成全新的 Stage 1.5J-B 生产回执（`stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z`），并通过领域严格加载器与独立 Rule 17 v2 结构验证器的双重闭环收敛审计。

**允许修改/写入的范围 (Mutable Scope):**
1. 单次生产授权文件：`.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/receipt_generation_authorization.txt` 及其 `.sha256`。
2. 目标回执目录：`data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z/**`。
3. 执行过程证据：`.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/evidence/**`。
4. 审计报告副本写入用户脑图目录：`/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/**`。

**绝对严禁触碰的范围 (Strict No-Touch Scope):**
- 任何现有代码文件（`src/**`, `scripts/**`, `tests/**`, `configs/**`）一律禁止修改。
- 上游 J-A 数据仓（`data/external_signal_shadow/stage1_5j_a/**`）完全只读。
- 两个既存 J-B legacy roots（`20261013T000000Z`, `20261013T040000Z`）保持只读且严禁覆盖。
- 严禁任何网络请求（`network_access_allowed=false`）。
- 全部 12 项治理 Authority Flags 必须保持为 `False`。
- `configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED` 必须保持为 `False`。

---

## 2. 任务分解与执行步骤 (Task Breakdown)

### Task 0: 准入基线与执行环境核查 (Preflight Verification)
- [ ] **Step 0.1: 核查当前 Git 状态与 HEAD**
  - 确认 `git status --porcelain` 为空（0 字节 dirty）。
  - 确认 `git rev-parse HEAD` 为 `1d445a23e9a742841d80b0997798caba530e8a94`。
- [ ] **Step 0.2: 核查权威组件 SHA-256**
  - `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` -> `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f`
  - `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py` -> `e2edcacc6de247ef344b4fb576a4dd5124f7e293e32660f8b9cad5ae86f9f74c`
  - `configs/stage1_5j_b_historical_aggtrades_launch_response.py` -> `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4`
  - `scripts/governance/verify_stage1_5j_b_receipt_schema.py` -> `442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1`
- [ ] **Step 0.3: 核查金融安全不变量**
  - 验证 `configs.base.RISK_LIVE_TRADING_ENABLED is False`。

---

### Task 1: 物化单次生产授权凭证 (Materialize Production Authorization Token)
- [ ] **Step 1.1: 组装精确的 8 字段授权文件**
  - 写入路径：`.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/receipt_generation_authorization.txt`
  - 内容严格为 ASCII / 无行内空格 / 单等号格式：
    ```text
    APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f
    APPROVED_J_B_PLAN_SHA256=1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd
    AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z
    AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4
    J_A_MANIFEST_SHA256=d47225c567bbcd6ea1ea14115e5ec0252119ebae4bfa021319206103328ce7d6
    NETWORK_ALLOWED=false
    AUDITED_J_B_CORE_SHA256=b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f
    AUDITED_J_B_CLI_SHA256=e2edcacc6de247ef344b4fb576a4dd5124f7e293e32660f8b9cad5ae86f9f74c
    ```
- [ ] **Step 1.2: 生成 `.sha256` 校验侧车**
  - 生成 `receipt_generation_authorization.txt.sha256` 并校验。
- [ ] **Step 1.3: 执行预检解析验证**
  - 运行 Python 诊断脚本调用内部 `_parse_receipt_generation_authorization`，确认解析成功且不抛出任何异常。

---

### Task 2: 执行生产运行并落盘新 Receipt (Production Execution)
- [ ] **Step 2.1: 调用生产 CLI 入口生成回执**
  - 执行命令：
    ```bash
    PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
      --run-id stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z
    ```
  - 要求退出码必须严格为 `0`。
- [ ] **Step 2.2: 验证回执文件结构与原子落盘**
  - 验证目标目录 `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z` 存在。
  - 验证封闭树仅包含 3 个标准产物：
    - `manifest.json`
    - `summary.json`
    - `review_CN.md`
  - 计算并记录 3 个产物的 SHA-256 与文件大小（预期总大小 < 1.0 MB，远低于 5.0 MB 上限）。

---

### Task 3: 双重严格验证 (Double Verification Gates)
- [ ] **Step 3.1: 运行 J-B 领域严格加载器 (Domain Strict Loader)**
  - 调用 `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root()`。
  - 确认：
    - `analysis_state == "launch_response_evidence_gap"`
    - `decision == "stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published"`
    - 281 个 child rows、843 个 child horizon rows、393 个 parent horizon rows
    - 重新比对 J-A 上游真值投影无偏差。
- [ ] **Step 3.2: 运行独立治理 Rule 17 v2 结构验证器 (Governance Schema Verifier)**
  - 执行命令：
    ```bash
    .venv/bin/python scripts/governance/verify_stage1_5j_b_receipt_schema.py \
      --profile stage1_5j_b_receipt_v2 \
      --artifact-root data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T033000Z
    ```
  - 要求退出码严格为 `0`。
- [ ] **Step 3.3: 静态质量与反捷径复查**
  - 运行 Ruff：`.venv/bin/ruff check src/ scripts/ tests/ configs/` -> `RC=0`。
  - 运行 Anti-shortcut scanner：`.venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha 1d445a23e9a742841d80b0997798caba530e8a94` -> `RC=0`。
  - 检查工作区 index 状态：`git status`（确认生产目录新增产物，核心代码 0 diff）。

---

### Task 4: 独立 Receipt Closure 审计 (Independent Receipt Closure Audit)
- [ ] **Step 4.1: 由独立审计员执行只读闭环核查**
  - 核查产物哈希与 manifest 对应一致性。
  - 验证全部 12 项治理 authority flags 均为 `False`。
  - 在隔离 `/tmp` 沙箱中执行至少 3 组负向变异探测（破坏 summary 字段、伪造 anchor 状态、破坏 manifest 签名），确认领域加载器与治理验证器均 fail-closed 拦截。
- [ ] **Step 4.2: 输出正式收敛凭证与审计报告**
  - 生成 `.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/evidence/v2_receipt_closure_evidence.json`（及 `.sha256`）。
  - 生成 `receipt_closure_audit_report.md`（及 `.sha256`）。
  - 归档审计报告副本至用户 brain 目录。
  - 给出终态结论：`RECEIPT_CLOSURE_AUDITED_POSITIVE`。

---

## 3. 验收标准与停止条件 (Acceptance & Stop Matrix)

| 触发场景 | 阻断分类 / 处置动作 |
| :--- | :--- |
| 当前 HEAD 与 `1d445a2` 不符 | `BLOCKED_SPEC_DRIFT`：立即中止 |
| `receipt_generation_authorization.txt` 存在格式缺陷或 SHA 不匹配 | `STOP=stage1_5j_b_receipt_authorization_invalid`：安全退出 (`rc=1`) |
| 目标目录已存在（命名碰撞） | `STOP=stage1_5j_b_output_collision`：禁止覆盖，必须更换 RUN_ID |
| 生产运行未生成合规三件套产物 | `STOP=stage1_5j_b_production_incomplete`：中止后续审计 |
| 领域加载器或治理验证器报 `rc != 0` | `STOP=receipt_closure_audit_failed`：调查缺陷并修复 |
| 存在任何网络连接尝试或非零 authority 权限提升 | 立即中止并抛出安全告警 |
