# Stage 1.5J-B Verified Archive Reduction Production Receipt Generation And Closure Audit Implementation Plan (R1)

> **For executor:** 仅在用户将本 Plan 纳入 Git 提交基线并以正式语句批准后，才可按 `.agent/workflows/execute-approved-plan.md` 逐 Task 执行。本 Plan 授权单次正式生成 Stage 1.5J-B 生产回执并进行独立双重闭环收敛审计。严禁 commit、push、deployment、SSH、网络请求、consumer 消费、replay 模拟、信号生成、模拟盘或实盘交易。

**状态:** `draft_for_user_approval`
**日期:** 2026-10-14
**前序受阻 Plan:** `docs/plans/2026-10-14-external-signal-shadow-lab-stage1-5j-b-verified-archive-reduction-production-receipt-generation-plan_CN.md` (SHA-256: `d78cb08836f0f34211d1679adb1cfd555ae31ad3be5d9e8bfb6b76a78b228000`)
**代码基线 Code BASE_SHA:** `1d445a23e9a742841d80b0997798caba530e8a94` (已合入且审计通过的流式归约修复代码)
**目标 RUN_ID:** `stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z`
**目标 Receipt 相对路径:** `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z`
**Plan identity:** `<APPROVED_PROFILE_PLAN_SHA256>` 只可由未来用户对本候选 exact bytes 的实施批准提供；本 Plan 不自引用、不生成或推断该值。

---

## 0. 修订控制与缺陷清结台账 (Closure Revision Ledger)

| 缺陷 ID | 级别 | 审计发现核心事实 | R1 修复动作与方案承诺 |
| :--- | :---: | :--- | :--- |
| **P0-01** | P0 | 原 Plan 自身为 untracked file，Task 0 声称 `git status --porcelain` 为空在逻辑上不可能成立。 | 本 Plan R1 必须在用户正式 commit 固化后启动执行；Task 0 执行时工作区 `git status --porcelain` 必须严格为 0 字节；目标使用全新 `AUTHORIZED_RUN_ID`（`20261014T044500Z`）；将此前生成的 `20261014T033000Z` 冻结为仅具诊断价值的非正向 legacy 证据。 |
| **P0-02** | P0 | 原计划及初版 R1 错误套用 J-A 命名规则生成 `v2_` 别名并指向普通执行账本，且未逐字列出 29 个字段、固定字面量、类型契约与来源，违反 J-B Rule 17 v2 冻结的权威治理路径，存在覆盖 `1ee...` legacy 闭环证据的风险。 | 严格恢复 J-B v2 规范契约：禁止使用任何 `v2_` 前缀别名；由独立 Receipt Closure Auditor 仅在专用的治理树路径 `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/` 下写入标准 `receipt_closure_evidence.json`；Task 4.2 逐字穷举全部 29 个顶级键、类型、固定 literal 与来源（要求审计时物理重算三件套哈希，要求用户批准 Plan SHA 必须严格匹配本 Plan 实际物理 SHA）；采用 canonical JSON 格式序列化及侧车 `<sha256>  receipt_closure_evidence.json\n`；绝对禁止覆盖现存 `1ee...` legacy closure 记录。 |
| **P0-03** | P0 | 原 Plan Step 3.3 要求全局 `ruff check src/ scripts/ tests/ configs/`，因无关遗留文件存在 20 处历史未使用导入而导致全局 RC=1 失败。 | 纠正门禁边界：Task 3 Step 3.3 严格针对 Stage 1.5J-B 专属白名单的 7 个核心组件文件执行 Ruff 检查（确认 0 error, RC=0），并要求工作区内核心代码相对 `BASE_SHA` 零新增代码改动，不跨范围修改无关历史脚本。 |

---

## 1. 绑定权威设计与契约矩阵 (Binding Authorities)

| 权威文件 | 相对路径 | SHA-256 | 约束管辖范围 |
| :--- | :--- | :--- | :--- |
| **Parent J-B Design** | `docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md` | `ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b` | 基础价格响应探索性问题定义、5m/1h/4h 窗口与中位数归约 |
| **Rebind Delta** | `docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md` | `0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c` | 上游 J-A replacement root 绑定、4 个文件摘要与 335/131/125/120/11/281 投影基准 |
| **Compatibility Domain Delta** | `docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md` | `66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f` | 阶段配置路径、9 个离线不可变常量与单次生产授权凭证结构 |
| **Governance Rule 17 v2 Delta** | `docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md` | `8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454` | 独立 `stage1_5j_b_receipt_v2` 结构验证器及封闭树校验规则与收敛凭据路径契约 |
| **Remediation Design Delta** | `docs/designs/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-design-delta_CN.md` | `7e305093027de1d7c9f3d3221aaa237def317c4033e4bed3e837697fe94c0a9d` | 流式归约缺陷修复（INV-JB-RR-01 ~ 05）及 Legacy Roots 废弃标记、闭环凭据无别名约束 |
| **Approved Remediation Plan** | `docs/plans/2026-10-13-external-signal-shadow-lab-stage1-5j-b-verified-archive-streaming-reduction-remediation-implementation-plan_CN.md` | `1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd` | 生产凭证所绑定的执行实施方案 SHA（代码中常量 `PLAN_SHA`） |

---

## 2. 目标与执行边界 (Goal and Scope Boundaries)

**目标:**
在工作区完全干净（已纳入 Git 提交基线、`git status --porcelain` 为 0 字节）、离线受控（单包 65536 字节缓冲上限）、无网络外联的条件下，针对上游 J-A 准入的 280 个币种归档重新调用生产 CLI，生成正向有效的 Stage 1.5J-B 生产回执（`stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z`），在专有治理树中生成精确规范的 `receipt_closure_evidence.json`，并通过领域严格加载器与独立 Rule 17 v2 结构验证器的双重闭环收敛审计。

**允许修改/写入的范围 (Mutable Scope):**
1. 单次生产授权文件：`.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/receipt_generation_authorization.txt` 及其 `.sha256`。
2. 目标回执目录：`data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z/**`。
3. 专用治理闭环证据目录：`.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/**`。
4. 审计报告副本写入用户脑图目录：`/Users/tanshuai/.gemini/antigravity/brain/76af4b6c-9a85-4949-9a67-72272139505c/**`。

**绝对严禁触碰的范围 (Strict No-Touch Scope):**
- 任何现有代码文件（`src/**`, `scripts/**`, `tests/**`, `configs/**`）一律禁止修改。
- 上游 J-A 数据仓（`data/external_signal_shadow/stage1_5j_a/**`）完全只读。
- 三个既存 J-B legacy roots（`20261013T000000Z`, `20261013T040000Z`, `20261014T033000Z`）保持只读且严禁覆盖。
- 现存治理闭环历史证据目录保持只读且严禁覆盖：
  - `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/ec5fbc3beeafd47ec42cdf12481751f41424fe3351a6c14845ebc0e5d5a8a319/**`
  - `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/**`
- 严禁任何网络请求（`network_access_allowed=false`）。
- 全部 12 项治理 Authority Flags 必须保持为 `False`。
- `configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED` 必须保持为 `False`。

---

## 3. 任务分解与执行步骤 (Task Breakdown)

### Task 0: 准入基线与执行环境核查 (Preflight Verification)
- [ ] **Step 0.1: 核查当前 Git 状态与纯净工作区**
  - 必须由用户首先将 Plan 文件提交到 Git，形成包含 Plan 的干净基线 Commit。
  - 确认 `git status --porcelain` 完全为空（**0 字节 dirty，解决 P0-01**）。
  - 确认 `git diff --quiet 1d445a23e9a742841d80b0997798caba530e8a94 -- src/ scripts/ configs/ tests/`（核心代码与已审计的 `1d445a2` 完全一致）。
- [ ] **Step 0.2: 核查权威组件 SHA-256**
  - `src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py` -> `b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f`
  - `scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py` -> `e2edcacc6de247ef344b4fb576a4dd5124f7e293e32660f8b9cad5ae86f9f74c`
  - `configs/stage1_5j_b_historical_aggtrades_launch_response.py` -> `771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4`
  - `scripts/governance/verify_stage1_5j_b_receipt_schema.py` -> `442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1`
- [ ] **Step 0.3: 核查金融安全不变量**
  - 验证 `configs.base.RISK_LIVE_TRADING_ENABLED is False`。

---

### Task 1: 物化全新单次生产授权凭证 (Materialize Production Authorization Token)
- [ ] **Step 1.1: 组装精确的 8 字段授权文件**
  - 写入路径：`.git/plan-execution/stage1_5j_b/1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd/receipt_generation_authorization.txt`
  - 内容严格为 ASCII / 无行内空格 / 单等号格式（绑定新 `AUTHORIZED_RUN_ID` 与代码中冻结的 `PLAN_SHA`）：
    ```text
    APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f
    APPROVED_J_B_PLAN_SHA256=1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd
    AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z
    AUDITED_J_B_CORE_SHA256=b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f
    AUDITED_J_B_CLI_SHA256=e2edcacc6de247ef344b4fb576a4dd5124f7e293e32660f8b9cad5ae86f9f74c
    AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4
    J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf
    NETWORK_ALLOWED=false
    ```
- [ ] **Step 1.2: 生成 `.sha256` 校验侧车**
  - 生成 `receipt_generation_authorization.txt.sha256` 并完成自检。
- [ ] **Step 1.3: 执行预检解析验证**
  - 调用内部 `_parse_receipt_generation_authorization`，确认解析成功（`keys=8`）。

---

### Task 2: 执行生产运行并原子落盘 (Production Execution)
- [ ] **Step 2.1: 调用生产 CLI 入口生成回执**
  - 执行命令：
    ```bash
    PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
      --run-id stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z
    ```
  - 要求退出码必须严格为 `0`。
- [ ] **Step 2.2: 验证回执文件结构与原子落盘**
  - 目标目录 `data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z` 存在。
  - 确认封闭树仅包含 3 个标准产物（`manifest.json`, `summary.json`, `review_CN.md`），无多余文件。
  - 记录 3 个产物的物理大小与 SHA-256。

---

### Task 3: 双重严格验证与质量门禁 (Double Verification Gates)
- [ ] **Step 3.1: 运行 J-B 领域公共严格语义加载器 (Domain Strict Loader)**
  - 调用 `load_verified_stage1_5j_b_historical_aggtrades_launch_response_root()`。
  - 确认全量重放 `analysis_state == "launch_response_evidence_gap"`、281/843/393 行，退出码严格为 `0`。
- [ ] **Step 3.2: 运行独立治理 Rule 17 v2 结构验证器 (Governance Schema Verifier)**
  - 执行命令：
    ```bash
    .venv/bin/python scripts/governance/verify_stage1_5j_b_receipt_schema.py \
      --profile stage1_5j_b_receipt_v2 \
      --artifact-root data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z
    ```
  - 要求退出码严格为 `0`。
- [ ] **Step 3.3: 静态质量与反捷径门禁 (解决 P0-03)**
  - 执行白名单专用 Ruff 检查：
    ```bash
    .venv/bin/ruff check \
      src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py \
      scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
      scripts/governance/verify_stage1_5j_b_receipt_schema.py \
      configs/stage1_5j_b_historical_aggtrades_launch_response.py \
      tests/research/external_signal_shadow/test_stage1_5j_b_historical_aggtrades_launch_response.py \
      tests/scripts/external_signal_shadow/test_run_stage1_5j_b_historical_aggtrades_launch_response.py \
      tests/scripts/governance/test_verify_stage1_5j_b_receipt_schema.py
    ```
    确认 `All checks passed!`, `RC=0`。
  - 运行 Anti-shortcut scanner：`.venv/bin/python .agent/tools/anti_shortcut_scan.py --base-sha 1d445a23e9a742841d80b0997798caba530e8a94` -> `RC=0`。
  - 验证 Git staged 为空：`git diff --cached --quiet`。

---

### Task 4: 独立 Receipt Closure 审计 (Independent Receipt Closure Audit)
- [ ] **Step 4.1: 执行隔离负向变异探测**
  - 在隔离 `/tmp` 沙箱中执行 4 组负向变异（伪造 anchor 状态、伪造 parent 状态、伪造配置 SHA、篡改 manifest 摘要），确认严格 fail-closed 拦截。
- [ ] **Step 4.2: 物化规范闭环证据工件 (解决 P0-02)**
  - **审批标识核查**: 核查用户实施批准语句中声明的 Plan SHA 必须与本 Plan 实际物理 SHA-256 严格一致，否则触发 `STOP=approved_profile_plan_identity_mismatch` 立即中止。由用户批准语句确立 `<APPROVED_PROFILE_PLAN_SHA256>`。
  - **证据目录路径**:
    - 目标凭据工件：`.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/receipt_closure_evidence.json`
    - 目标校验侧车：`.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/receipt_closure_evidence.json.sha256`
  - **工件命名规则**: 严格命名为 `receipt_closure_evidence.json`，严禁使用任何 `v2_` 前缀别名。
  - **三件套哈希重算**: 独立审计员必须从目标回执物理文件重新计算最新 SHA-256：
    - `manifest_sha256`: 重新计算目标回执 `manifest.json` 物理字节的 64 位小写十六进制 SHA-256。
    - `summary_sha256`: 重新计算目标回执 `summary.json` 物理字节的 64 位小写十六进制 SHA-256。
    - `review_sha256`: 重新计算目标回执 `review_CN.md` 物理字节的 64 位小写十六进制 SHA-256。
  - **精确 29 键字典与类型契约**: 必须逐字包含以下全部 29 个平面顶级键，严禁任何嵌套对象、别名、遗漏或额外键：
    1. `audited_config_relative_path` (str): `"configs/stage1_5j_b_historical_aggtrades_launch_response.py"` (冻结配置相对路径)
    2. `audited_config_sha256` (str): `"771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4"` (冻结配置源码 SHA)
    3. `domain_loader_expected_rc` (int): `0` (非布尔整型，期望领域严格加载器返回码)
    4. `domain_loader_observed_rc` (int): `0` (非布尔整型，实际观察到的领域加载器返回码)
    5. `evidence_status` (str): `"receipt_closure_audited_positive"` (固定权威收敛状态)
    6. `governance_parent_design_relative_path` (str): `"docs/designs/2026-10-09-governance-cross-boundary-artifact-schema-integrity-design_CN.md"` (父级治理设计路径)
    7. `governance_parent_design_sha256` (str): `"73006481a7a390213e7912d2bc5fb04d61dde77088176d82547cf9110951e4f4"` (父级治理设计 SHA)
    8. `governance_rule17_j_b_v2_positive` (bool): `True` (严格布尔真值，表示 Rule 17 v2 审计正向闭环)
    9. `j_b_compatibility_domain_delta_relative_path` (str): `"docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md"` (兼容性域设计路径)
    10. `j_b_compatibility_domain_delta_sha256` (str): `"66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f"` (兼容性域设计 SHA)
    11. `j_b_parent_design_relative_path` (str): `"docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md"` (J-B 父级设计路径)
    12. `j_b_parent_design_sha256` (str): `"ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b"` (J-B 父级设计 SHA)
    13. `j_b_profile_v2_design_relative_path` (str): `"docs/designs/2026-10-12-governance-stage1-5j-b-receipt-rule17-profile-v2-design-delta_CN.md"` (治理 v2 Profile 设计路径)
    14. `j_b_profile_v2_design_sha256` (str): `"8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454"` (治理 v2 Profile 设计 SHA)
    15. `j_b_rebind_delta_relative_path` (str): `"docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md"` (J-B 重新绑定设计路径)
    16. `j_b_rebind_delta_sha256` (str): `"0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c"` (J-B 重新绑定设计 SHA)
    17. `j_b_receipt_schema_authority_relative_path` (str): `"docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md"` (模式权威设计路径)
    18. `j_b_receipt_schema_authority_sha256` (str): `"f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25"` (模式权威设计 SHA)
    19. `manifest_sha256` (str): 审计重算的 64 位小写十六进制 SHA
    20. `profile_contract_version` (int): `2` (非布尔整型，固定版本 2)
    21. `profile_id` (str): `"stage1_5j_b_receipt_v2"` (固定 Profile 标识)
    22. `receipt_root_relative_path` (str): `"data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"` (本次生产回执根相对路径)
    23. `receipt_run_id` (str): `"stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"` (本次生产回执 RUN_ID，必须与路径末级严格一致)
    24. `review_sha256` (str): 审计重算的 64 位小写十六进制 SHA
    25. `summary_sha256` (str): 审计重算的 64 位小写十六进制 SHA
    26. `verifier_expected_rc` (int): `0` (非布尔整型，期望治理验证器返回码)
    27. `verifier_observed_rc` (int): `0` (非布尔整型，实际观察到的治理验证器返回码)
    28. `verifier_relative_path` (str): `"scripts/governance/verify_stage1_5j_b_receipt_schema.py"` (独立治理验证器脚本路径)
    29. `verifier_source_sha256` (str): `"442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1"` (已审计独立的治理验证器源码 SHA)
  - **规范序列化与侧车生成**:
    - 证据字节格式：`json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"`
    - 侧车内容格式：`<evidence_sha256>  receipt_closure_evidence.json\n`（其中 `<evidence_sha256>` 为证据字节小写 SHA-256，后跟两个 ASCII 空格）
  - **历史遗留证据保护**: 绝对禁止修改或覆盖现有 `1ee...` legacy closure 记录。
- [ ] **Step 4.3: 输出正式收敛审计报告**
  - 生成 `.git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/<APPROVED_PROFILE_PLAN_SHA256>/evidence/receipt_closure_audit_report.md`（及 `.sha256`）。
  - 归档报告副本至用户 brain 目录。
  - 给出终态结论：`RECEIPT_CLOSURE_AUDITED`。

---

## 4. 验收标准与停止条件 (Acceptance & Stop Matrix)

| 触发场景 | 阻断分类 / 处置动作 |
| :--- | :--- |
| Task 0 启动时 `git status --porcelain` 不为空 | `STOP=worktree_not_clean_must_commit_plan_first`：立即中止 |
| 用户批准语句中的 Plan SHA 与实际 Plan SHA 不一致 | `STOP=approved_profile_plan_identity_mismatch`：立即中止 |
| 核心代码相对 `1d445a2` 存在任何 diff | `BLOCKED_SCOPE_DRIFT`：立即中止 |
| `receipt_generation_authorization.txt` 存在格式缺陷或 SHA 不匹配 | `STOP=stage1_5j_b_receipt_authorization_invalid`：安全退出 (`rc=1`) |
| 目标目录已存在（命名碰撞） | `STOP=stage1_5j_b_output_collision`：禁止覆盖，必须更换 RUN_ID |
| 领域加载器或治理验证器报 `rc != 0` | `STOP=receipt_closure_audit_failed`：调查缺陷并修复 |
| 闭环凭据未在治理专属树下精确物化或使用了 `v2_` 别名 | `STOP=closure_evidence_identity_mismatch`：拒绝收敛 |
| 尝试覆盖 `1ee...` legacy 闭环证据 | `STOP=legacy_closure_evidence_immutable`：立即中止 |
| 存在任何网络连接尝试或非零 authority 权限提升 | 立即中止并抛出安全告警 |
