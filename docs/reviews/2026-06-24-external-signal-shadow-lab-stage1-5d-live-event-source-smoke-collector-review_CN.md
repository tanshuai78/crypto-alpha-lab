# Stage 1.5D Live Event-Source Smoke Collector Review

## Decision
- 决策: stage1_5d_smoke_observation_in_progress
- 是否成功验证事件检测 (event_detection_validated): False
- 是否符合研究结论 (research_result_valid): False

## Upstream Evidence Gate
- 上游证据验证结果: 通过
- 异常阻碍器 (blockers): []

## Polling Health
- 轮询次数 (poll_count): 3
- 运行小时数 (observation_hours): 0.0038h
- 是否为 Fixture 运行 (fixture_run): False
- 是否为 Short Debug 运行 (debug_short_run): True

## Event Detection
- 检测到新的合约上线事件数量: 28
- 原始 futures launch 文章计数 (raw_futures_launch_article_count): 84
- 成功解析 symbol 的事件计数 (symbol_parsed_event_count): 42
- symbol 解析失败事件计数 (symbol_parse_failed_count): 42
- 跨 poll 去重后的新事件计数 (deduped_new_event_count): 28

## First Futures Bar Observation
- 对首个期货 K 线 (first futures bar) 的观察状态记录: 观察进行中或尚未检测到事件

## Safety Boundaries
- 是否允许模拟交易 (paper_trading_allowed): False
- 是否允许实盘交易 (live_trading_allowed): False
- 是否允许执行引擎启动 (execution_engine_allowed): False
- 是否允许 Alpha 解释 (alpha_interpretation_allowed): False

## Allowed Next Action
- 下一步允许动作: 继续保持 shadow 观察或排查 polling/upstream 错误

## 24h Live Smoke 操作说明

### 1. 当前命令是不是后台运行？

不是。

下面这种直接执行方式是**前台运行**：

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  --output-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --poll-interval-sec 60 \
  --max-seconds 86400 \
  --live-public-readonly
```

判断标准：

- 如果终端没有返回 shell prompt，程序仍在前台运行。
- 如果 SSH 断开或关闭终端，前台程序通常会被终止。
- 程序运行时没有持续打印日志是正常现象；它主要写入 `data/external_signal_shadow/stage1_5d/live_event_source_smoke/` 下的 JSONL 文件，结束时才写 summary。

如果要后台长期跑，建议使用 `tmux` 或 `screen`，不要裸跑在普通 SSH 窗口里。

### 2. 如何确认程序还在运行？

在另一个终端执行：

```bash
ps aux | rg 'run_stage1_5d_live_event_source_smoke_collector|stage1_5d'
```

检查最近 heartbeat：

```bash
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/heartbeats/*.jsonl
```

检查 request manifest 是否持续增长：

```bash
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
```

### 3. 24h 推荐运行方式

推荐用 `tmux`：

```bash
tmux new -s stage1_5d
```

进入 `tmux` 后运行：

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  --output-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --poll-interval-sec 60 \
  --max-seconds 86400 \
  --live-public-readonly
```

离开 `tmux` 但不中断程序：

```text
Ctrl-b 然后按 d
```

重新进入：

```bash
tmux attach -t stage1_5d
```

### 4. 如果 24h 内人为中断会怎样？

如果用 `Ctrl-C` 或 SSH 断开导致程序中断：

- 已经写入的 `events` / `heartbeats` / `raw_payloads` / `request_manifest` JSONL 通常会保留。
- 当前 run 的最终 summary 可能不会更新，或者仍保留上一次 summary。
- `observation_hours` 不会达到 24h，因此不能判定为正式 operational pass。
- 中断后重新运行，进程内 `seen_event_ids` 会重置；如果继续写同一个 `output-root`，同一日 `events/*.jsonl` 可能出现跨 run 重复行。

因此，如果只是临时测试，可以中断。

如果目标是正式 24h source smoke，建议中断后重新开始一个干净 run：

```bash
mv data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  data/external_signal_shadow/stage1_5d/live_event_source_smoke_interrupted_$(date +%Y%m%d_%H%M%S)

mkdir -p data/external_signal_shadow/stage1_5d/live_event_source_smoke
```

然后重新执行 24h 命令。

### 5. 中途巡检命令

查看 summary：

```bash
cat data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

注意：程序正常结束前，summary 可能不会实时更新。更可靠的是看 heartbeat 和 manifest。

查看 heartbeat：

```bash
tail -n 10 data/external_signal_shadow/stage1_5d/live_event_source_smoke/heartbeats/*.jsonl
```

查看请求记录：

```bash
tail -n 10 data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
```

查看事件：

```bash
wc -l data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
```

### 6. 跑完后生成 review

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5d_live_event_source_smoke_collector.py \
  --summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --output-review docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

### 7. 结果解释

如果 24h 后仍然没有捕捉到真实新事件，理想结果是：

```text
decision = stage1_5d_operational_pass_event_detection_unvalidated
research_result_valid = true
event_detection_validated = false
```

含义：公告源和 collector 运行稳定，但 24h 内没有验证到真实新 futures launch 事件。

如果捕捉到新 futures launch 且观察到 first futures bar，理想结果是：

```text
decision = stage1_5d_event_detection_passed
research_result_valid = true
event_detection_validated = true
```

含义：live event source detection 路径闭环。

如果出现 `blockers`，不要进入下一阶段，先修 source / parser / network / storage 问题。

## 服务器部署 / 运行 / 检查 / 取回数据流程

### 1. 适用场景

如果本地笔记本无法连续运行 24h，应在服务器上跑正式 24h source smoke。

服务器运行的目标是验证：

```text
collector 能否连续运行 >= 24h
Binance public announcement source 是否稳定
heartbeat / request_manifest 是否持续写入
是否能检测 futures_contract_launch 文章
是否能观察 first futures bar
```

本阶段仍然是 source smoke：

```text
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

### 2. 部署前检查

在服务器执行：

```bash
cd /root/crypto-alpha-lab
python3 --version
PYTHONPATH=src:. python3 scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py --help
```

如果 `--help` 能输出参数列表，说明脚本路径和 Python import 基本可用。

检查上游证据文件：

```bash
ls -lh data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json
ls -lh data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

如果缺失，先从本地同步：

```bash
ssh root@47.82.4.85 'mkdir -p /root/crypto-alpha-lab/data/external_signal_shadow/stage1_5c1/price_coverage /root/crypto-alpha-lab/data/external_signal_shadow/stage1_5c'

scp data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  root@47.82.4.85:/root/crypto-alpha-lab/data/external_signal_shadow/stage1_5c1/price_coverage/

scp data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  root@47.82.4.85:/root/crypto-alpha-lab/data/external_signal_shadow/stage1_5c/
```

检查上游证据内容：

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=src:. python3 - <<'PY'
import json
from pathlib import Path

paths = [
    Path("data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json"),
    Path("data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json"),
]

for p in paths:
    print("\n==", p, "==")
    if not p.exists():
        print("MISSING")
        continue
    data = json.loads(p.read_text())
    for k in [
        "decision",
        "top_level_decision",
        "research_result_valid",
        "promising_cells",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_engine_allowed",
        "alpha_interpretation_allowed",
    ]:
        if k in data:
            print(k, "=", data[k])
PY
```

必须满足：

```text
Stage 1.5C.1 decision = stage1_5c1_price_coverage_ready_for_1_5c_rerun
Stage 1.5C top_level_decision = stage1_5c_replay_completed
Stage 1.5C research_result_valid = true
Stage 1.5C promising_cells 包含 futures_contract_launch / futures_launch_long_attention_diagnostic / 12h
paper/live/execution/alpha flags 不能为 true
```

如果启动时报：

```text
Error: upstream evidence invalid
```

说明上述文件缺失、内容过旧、或不满足 gate。先修上游文件，不要绕过 gate。

### 3. 服务器启动方式

推荐使用 `tmux`：

```bash
ssh root@47.82.4.85
用更稳的登录方式是：同时把提示符改回方便一点，可以直接在登录时手动设 PS1
ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -tt root@47.82.4.85 'env -u TMOUT PS1="\u@\h:\w\$ " bash --noprofile --norc -i'
cd /root/crypto-alpha-lab
tmux new -s stage1_5d
```

在 `tmux` 内执行：

```bash
cd /root/crypto-alpha-lab

PYTHONPATH=src:. python3 scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  --stage1-5c1-summary data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json \
  --stage1-5c-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-root data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  --output-summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --poll-interval-sec 60 \
  --max-seconds 86400 \
  --live-public-readonly
```

说明：

- 服务器上如果 `uv` 不可用，可以直接用 `python3`，当前脚本支持这种方式。
- 执行后终端长时间无输出是正常现象。
- 程序主要写 JSONL，结束时才写 summary。

离开 `tmux` 但不中断程序：

```text
Ctrl-b 然后按 d
```

重新进入：

```bash
tmux attach -t stage1_5d
```

### 4. 如何检查方案 B 是否正在运行

检查进程：

```bash
ps aux | grep run_stage1_5d_live_event_source_smoke_collector | grep -v grep
```

如果有输出，说明进程仍在。

检查 `tmux` session：

```bash
tmux ls
```

检查 heartbeat 是否持续增长：

```bash
cd /root/crypto-alpha-lab
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/heartbeats/*.jsonl
```

检查请求记录：

```bash
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
```

检查事件文件：

```bash
wc -l data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/events/*.jsonl
```

注意：

- summary 在程序结束前可能不会实时更新。
- 中途判断运行状态，优先看 `heartbeats/*.jsonl` 和 `request_manifest/*.jsonl`。

### 5. 中途异常判断

如果 `ps` 查不到进程，说明程序已退出或被中断。

查看是否已有 summary：

```bash
cat data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
```

查看最近请求是否有错误：

```bash
tail -n 20 data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
```

常见情况：

```text
Error: upstream evidence invalid
```

含义：上游 summary 文件缺失或不满足 gate。

```text
没有输出，但 ps 能看到进程
```

含义：正常前台/tmux 运行，等待 24h 结束。

```text
heartbeat 不增长，ps 也查不到进程
```

含义：进程已退出，需要检查 summary / manifest 后决定是否重新跑。

### 6. 如果中断，如何重新开始干净 run

如果目标是正式 24h source smoke，中断后不要拼接多段运行。

先归档旧目录：

```bash
cd /root/crypto-alpha-lab
mv data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  data/external_signal_shadow/stage1_5d/live_event_source_smoke_interrupted_$(date +%Y%m%d_%H%M%S)

mkdir -p data/external_signal_shadow/stage1_5d/live_event_source_smoke
```

然后重新运行完整 24h 命令。

正式 24h 判定必须来自同一次连续运行：

```text
observation_hours >= 24
fixture_run = false
debug_short_run = false
blockers = []
```

### 7. 24h 结束后在服务器生成 review

运行结束后：

```bash
cd /root/crypto-alpha-lab

PYTHONPATH=src:. python3 scripts/external_signal_shadow/review_stage1_5d_live_event_source_smoke_collector.py \
  --summary data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json \
  --output-review docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

查看结果：

```bash
cat data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
sed -n '1,220p' docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md
```

### 8. 从服务器取回数据

在本地执行：

```bash
mkdir -p data/external_signal_shadow/stage1_5d

rsync -av root@47.82.4.85:/root/crypto-alpha-lab/data/external_signal_shadow/stage1_5d/live_event_source_smoke \
  data/external_signal_shadow/stage1_5d/

scp root@47.82.4.85:/root/crypto-alpha-lab/docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md \
  docs/reviews/
```

取回后本地检查：

```bash
cat data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/heartbeats/*.jsonl
tail -n 5 data/external_signal_shadow/stage1_5d/live_event_source_smoke/request_manifest/*.jsonl
```

### 9. 结果通过 / 不通过的判断

Operational pass，但未捕捉到真实新事件：

```text
decision = stage1_5d_operational_pass_event_detection_unvalidated
research_result_valid = true
event_detection_validated = false
```

含义：源和 collector 连续运行稳定，但 24h 内没有真实 futures launch 新事件完成 first-bar 观察。

Event detection pass：

```text
decision = stage1_5d_event_detection_passed
research_result_valid = true
event_detection_validated = true
```

含义：公告检测、事件解析、first futures bar observation 路径闭环。

不通过：

```text
decision = stage1_5d_smoke_failed
或
decision = stage1_5d_smoke_invalid
或
blockers 非空
```

含义：不要进入下一阶段，先修 source / parser / network / storage / upstream evidence。
