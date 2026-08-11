# Stage 1.5D/1.5F Git Ancestry Attestation Deployment Checklist

**日期：** 2026-08-10
**状态：** approved for disabled-producer deployment

---

## Section A: Current Disabled Deployment (Runnable Read-Only Operational Checks)

在常规只读部署模式下，`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED` 保持 `False`。以下所有命令均为只读与验证状态命令：

1. **检查 Git 工作树与 HEAD 状态：**

```bash
git status --short
git rev-parse HEAD
```

2. **验证 Producer 仍然配置为关闭状态：**

```bash
python3 -c "from configs import base; print('PRODUCER_ENABLED:', base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED)"
```

3. **验证 1.5D 生成的 Events 与 Runtime Gate Artifacts：**

```bash
test -f data/external_signal_shadow/stage1_5d/live_event_source_smoke/live_safety_gate_summary.json
ls -l data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
```

4. **检查 1.5D Runtime Gate 中的 Output Root ID：**

```bash
python3 -c "import json; g = json.load(open('data/external_signal_shadow/stage1_5d/live_event_source_smoke/live_safety_gate_summary.json')); print('root_id:', g.get('stage1_5d_output_root_id'))"
```

5. **检查 1.5F Observer Root Contract 与 Summary：**

```bash
test -f data/external_signal_shadow/stage1_5f/live_depth_observer/observer_root_contract.json
test -f data/external_signal_shadow/stage1_5f/live_depth_observer/live_depth_observer_summary.json
```

---

## Section B: Future Enablement Reference (Non-Executable Specification)

仅作为未来由独立评估决策开启 Producer 时的顺序与验证逻辑参考（本文件不提供任何可自动调用的开启命令）：

1. **E0 (Bootstrap Waiting for Consumer):**
   - 开启 producer 配置 (`PRODUCER_ENABLED = True`)。
   - 1.5D 启动时校验静态证明与 Git Ancestry (Commit A -> Commit B)。
   - 由于未配置/提供 1.5F 的 `--stage1-5f-consumer-root-contract` 与 `--stage1-5f-consumer-summary` 路径，1.5D 报告 `BOOTSTRAP_WAITING_FOR_CONSUMER`，`effective_enabled` 为 `False`。
   - 常规 Launch Collection 正常进行，仅 formal revision 不会被发散。

2. **E1 (Consumer Proof Arming):**
   - 1.5F Observer 在同 output root 和同 HEAD 提交下启动。
   - 1.5F 发布 `observer_root_contract.json` 与 `live_depth_observer_summary.json`，其中记录由 `Path.resolve()` 计算的源 1.5D 三重 Output Root ID 绑定。
   - 在后续 poll 周期中，1.5D 读取并原子化验证 1.5F 的 static proof、root contract hash、startup SHA 以及 canonical manifest hash。
   - 验证通过后，1.5D 正式 arm，允许 `effective_enabled = True`。

3. **E2 (Restart & Sticky Latch Protection):**
   - 1.5D 在同一 Output Root 下重启，依然能基于 1.5F 现存且匹配的 Root Contract 与 Summary 重新 arm。
   - 一旦 1.5F 进程发生重启 (Process Instance ID 改变)、Root Contract / Summary 签名不匹配或工作树发生修改，1.5D 会永久 latch sticky compromised 并即刻 fail-closed（仅阻止 formal revision 广播）。
