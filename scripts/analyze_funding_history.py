"""
scripts/analyze_funding_history.py
-----------------------------------
离线历史回放：Extreme Funding Scanner
用途：在接 API 之前，先验证"极端资金费率事件"在过去 74 天的历史中实际出现了多少次、
      频率如何、持续多长时间、理论 P&L 能否覆盖成本。

数据来源：旧项目 data/historical_orderbook/ 目录（不复制，只读引用）
运行方式：
    cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
    uv run python scripts/analyze_funding_history.py

输出：
    - 控制台：每个 Symbol 的汇总统计
    - data/funding_analysis_result.json：可供后续脚本消费的结构化结果
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

# ─── 配置 ──────────────────────────────────────────────────────────────────────

# 旧项目历史数据路径（只读引用，不复制）
HISTORICAL_DATA_DIR = Path(
    "/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook"
)

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "funding_analysis_result.json"

# 分析参数（与 configs/base.py 中的策略参数对齐）
SETTLEMENTS_PER_DAY = 3          # Binance/OKX 每天 3 次 (0/8/16 UTC)
ANNUALIZED_MULTIPLIER = SETTLEMENTS_PER_DAY * 365  # 1095

EXTREME_FUNDING_THRESHOLD_PCT = 30.0   # 极端事件门槛：年化 > 30%
PERSISTENCE_WINDOW = 20                # 用最近 N 个样本计算 Persistence
PERSISTENCE_MIN = 0.70                 # Persistence 门槛：70% 为正

# 成本模型（与 cost_model.py 对齐）
TAKER_FEE_BPS = 5.0       # 双边 Taker 手续费（各 0.05%）
SLIPPAGE_BPS = 3.0        # 保守滑点估算（单边 1.5 bps）
ROUND_TRIP_COST_BPS = (TAKER_FEE_BPS * 2) + (SLIPPAGE_BPS * 2)  # 单次完整套利

# 极端事件持仓假设
MAX_HOLDING_HOURS = 24    # 最大持仓 24 小时（3 次结算）

# 关注的 Symbol（与旧系统同步）
TARGET_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT", "DOGE/USDT"]

# ─── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class FundingSnapshot:
    ts_ms: int
    symbol: str
    exchange: str
    funding_rate: float
    mark_price: float

    @property
    def annualized_pct(self) -> float:
        return self.funding_rate * ANNUALIZED_MULTIPLIER * 100

    @property
    def dt(self) -> datetime:
        return datetime.fromtimestamp(self.ts_ms / 1000, tz=timezone.utc)


@dataclass
class ExtremeEvent:
    symbol: str
    exchange: str
    start_dt: datetime
    end_dt: datetime
    peak_annualized_pct: float
    avg_annualized_pct: float
    avg_persistence: float
    settlement_count: int  # 预计结算次数（持仓时间内）
    gross_funding_income_bps: float
    net_edge_bps: float    # 扣除手续费和滑点后

    @property
    def duration_hours(self) -> float:
        return (self.end_dt - self.start_dt).total_seconds() / 3600

    @property
    def is_profitable(self) -> bool:
        return self.net_edge_bps > 0


@dataclass
class SymbolSummary:
    symbol: str
    exchange: str
    total_snapshots: int = 0
    date_range: tuple[str, str] = ("", "")
    extreme_events: list[ExtremeEvent] = field(default_factory=list)

    @property
    def event_count(self) -> int:
        return len(self.extreme_events)

    @property
    def profitable_event_count(self) -> int:
        return sum(1 for e in self.extreme_events if e.is_profitable)

    @property
    def avg_net_edge_bps(self) -> float:
        if not self.extreme_events:
            return 0.0
        return sum(e.net_edge_bps for e in self.extreme_events) / len(self.extreme_events)


# ─── 数据读取 ──────────────────────────────────────────────────────────────────

def iter_funding_files(exchange: str) -> list[Path]:
    """按日期排序返回所有 funding 数据文件"""
    pattern = f"{exchange}_funding_*.jsonl"
    files = sorted(HISTORICAL_DATA_DIR.glob(pattern))
    return files


def read_funding_snapshots(exchange: str, target_symbol: str) -> Iterator[FundingSnapshot]:
    """流式读取指定 exchange + symbol 的所有 funding rate 记录"""
    # Binance 用 "BTC/USDT"，OKX 用 "BTC/USDT:USDT"
    if exchange == "okx":
        base = target_symbol.split("/")[0]
        okx_symbol = f"{base}/USDT:USDT"
        match_symbols = {okx_symbol}
    else:
        match_symbols = {target_symbol}

    for filepath in iter_funding_files(exchange):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if rec.get("symbol") not in match_symbols:
                        continue
                    if rec.get("type") != "funding_rate":
                        continue

                    fr = rec.get("funding_rate")
                    mp = rec.get("mark_price")
                    ts = rec.get("timestamp")

                    if fr is None or ts is None:
                        continue

                    yield FundingSnapshot(
                        ts_ms=int(ts),
                        symbol=target_symbol,
                        exchange=exchange,
                        funding_rate=float(fr),
                        mark_price=float(mp) if mp else 0.0,
                    )
        except Exception as e:
            print(f"  [WARN] Error reading {filepath.name}: {e}", file=sys.stderr)


# ─── 核心分析逻辑 ──────────────────────────────────────────────────────────────

def compute_persistence(window: list[FundingSnapshot]) -> float:
    """计算最近 N 个样本中资金费率为正的比例"""
    if not window:
        return 0.0
    positive = sum(1 for s in window if s.funding_rate > 0)
    return positive / len(window)


def detect_extreme_events(
    snapshots: list[FundingSnapshot],
    threshold_pct: float = EXTREME_FUNDING_THRESHOLD_PCT,
    persistence_min: float = PERSISTENCE_MIN,
) -> list[ExtremeEvent]:
    """
    检测极端资金费率事件。
    事件定义：annualized > threshold_pct AND persistence > persistence_min
    连续满足条件的样本合并为一个事件。
    """
    if not snapshots:
        return []

    events: list[ExtremeEvent] = []
    window: list[FundingSnapshot] = []
    in_event = False
    event_snapshots: list[FundingSnapshot] = []

    for snap in snapshots:
        window.append(snap)
        if len(window) > PERSISTENCE_WINDOW:
            window.pop(0)

        persistence = compute_persistence(window)
        is_extreme = (
            abs(snap.annualized_pct) >= threshold_pct
            and persistence >= persistence_min
        )

        if is_extreme and not in_event:
            in_event = True
            event_snapshots = [snap]
        elif is_extreme and in_event:
            event_snapshots.append(snap)
        elif not is_extreme and in_event:
            # 事件结束，计算统计
            ev = _build_event(event_snapshots)
            if ev:
                events.append(ev)
            in_event = False
            event_snapshots = []

    # 处理末尾未结束的事件
    if in_event and event_snapshots:
        ev = _build_event(event_snapshots)
        if ev:
            events.append(ev)

    return events


def _build_event(snaps: list[FundingSnapshot]) -> ExtremeEvent | None:
    if not snaps:
        return None

    ann_values = [s.annualized_pct for s in snaps]
    peak = max(ann_values, key=abs)
    avg_ann = sum(ann_values) / len(ann_values)

    # 建立本地 window 计算 persistence（用全部 event 样本中的正值比例）
    positive_count = sum(1 for s in snaps if s.funding_rate > 0)
    avg_persistence = positive_count / len(snaps)

    start_dt = snaps[0].dt
    end_dt = snaps[-1].dt
    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    # 预计结算次数（每 8 小时一次结算）
    settlement_count = max(1, int(duration_hours / 8))
    # 限制在最大持仓范围内
    settlement_count = min(settlement_count, MAX_HOLDING_HOURS // 8)

    # 每次结算的资金收益（以 bps 为单位）
    avg_rate_bps = (avg_ann / 100) / ANNUALIZED_MULTIPLIER * 10_000  # per settlement in bps
    gross_funding_income_bps = avg_rate_bps * settlement_count

    # 净收益 = 资金收入 - 手续费 - 滑点
    net_edge_bps = gross_funding_income_bps - ROUND_TRIP_COST_BPS

    return ExtremeEvent(
        symbol=snaps[0].symbol,
        exchange=snaps[0].exchange,
        start_dt=start_dt,
        end_dt=end_dt,
        peak_annualized_pct=peak,
        avg_annualized_pct=avg_ann,
        avg_persistence=avg_persistence,
        settlement_count=settlement_count,
        gross_funding_income_bps=round(gross_funding_income_bps, 2),
        net_edge_bps=round(net_edge_bps, 2),
    )


# ─── 主流程 ────────────────────────────────────────────────────────────────────

def analyze_symbol(exchange: str, symbol: str) -> SymbolSummary:
    summary = SymbolSummary(symbol=symbol, exchange=exchange)

    snaps = list(read_funding_snapshots(exchange, symbol))
    summary.total_snapshots = len(snaps)

    if not snaps:
        return summary

    snaps.sort(key=lambda s: s.ts_ms)
    summary.date_range = (
        snaps[0].dt.strftime("%Y-%m-%d"),
        snaps[-1].dt.strftime("%Y-%m-%d"),
    )

    summary.extreme_events = detect_extreme_events(snaps)
    return summary


def print_summary(summary: SymbolSummary) -> None:
    sym_tag = f"{summary.exchange.upper()} {summary.symbol}"
    print(f"\n{'='*60}")
    print(f"  {sym_tag}")
    print(f"{'='*60}")
    print(f"  数据量：{summary.total_snapshots:,} 条样本")
    print(f"  时间范围：{summary.date_range[0]} → {summary.date_range[1]}")
    print(f"  极端事件总数：{summary.event_count} 次")

    if summary.event_count == 0:
        print("  → 在门槛条件下未检测到极端资金费率事件")
        return

    print(f"  净正收益事件：{summary.profitable_event_count} / {summary.event_count}")
    print(f"  平均净 Edge：{summary.avg_net_edge_bps:.1f} bps")
    print()

    for i, ev in enumerate(summary.extreme_events, 1):
        profitable_flag = "✅" if ev.is_profitable else "❌"
        print(
            f"  [{i:02d}] {profitable_flag} "
            f"{ev.start_dt.strftime('%m-%d %H:%M')} UTC → "
            f"{ev.end_dt.strftime('%m-%d %H:%M')} UTC "
            f"({ev.duration_hours:.1f}h)"
        )
        print(
            f"       峰值年化：{ev.peak_annualized_pct:+.1f}%  "
            f"均值年化：{ev.avg_annualized_pct:+.1f}%  "
            f"Persistence：{ev.avg_persistence:.0%}"
        )
        print(
            f"       预计结算：{ev.settlement_count} 次  "
            f"毛收益：{ev.gross_funding_income_bps:.1f} bps  "
            f"净 Edge：{ev.net_edge_bps:+.1f} bps  "
            f"（成本：{ROUND_TRIP_COST_BPS:.0f} bps）"
        )


def main() -> None:
    print("=" * 60)
    print("  Extreme Funding Scanner — 历史回放分析")
    print(f"  数据目录：{HISTORICAL_DATA_DIR}")
    print(f"  门槛：年化 > {EXTREME_FUNDING_THRESHOLD_PCT}%，Persistence > {PERSISTENCE_MIN:.0%}")
    print(f"  成本假设：双边手续费 {TAKER_FEE_BPS*2:.0f} bps + 滑点 {SLIPPAGE_BPS*2:.0f} bps = {ROUND_TRIP_COST_BPS:.0f} bps")
    print("=" * 60)

    all_summaries = []
    grand_total_events = 0

    for exchange in ["binance", "okx"]:
        for symbol in TARGET_SYMBOLS:
            print(f"\n分析中：{exchange.upper()} {symbol} ...", end="", flush=True)
            summary = analyze_symbol(exchange, symbol)
            print(f" {summary.total_snapshots:,} 条 → {summary.event_count} 次极端事件")
            print_summary(summary)
            all_summaries.append(summary)
            grand_total_events += summary.event_count

    # 全局汇总
    print(f"\n\n{'='*60}")
    print("  全局汇总")
    print(f"{'='*60}")
    print(f"  覆盖 Symbol：{len(TARGET_SYMBOLS)} 个，交易所：2 个（Binance + OKX）")
    print(f"  极端事件总计：{grand_total_events} 次")

    profitable_total = sum(s.profitable_event_count for s in all_summaries)
    if grand_total_events > 0:
        win_rate = profitable_total / grand_total_events
        print(f"  净正收益事件：{profitable_total} 次（胜率 {win_rate:.0%}）")

    # 找出 peak event
    all_events = [ev for s in all_summaries for ev in s.extreme_events]
    if all_events:
        best = max(all_events, key=lambda e: e.net_edge_bps)
        worst = min(all_events, key=lambda e: e.net_edge_bps)
        print(f"  最佳 Net Edge：{best.net_edge_bps:+.1f} bps")
        print(f"    → {best.exchange.upper()} {best.symbol} @ {best.start_dt.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"    → 峰值年化：{best.peak_annualized_pct:+.1f}%，持续 {best.duration_hours:.1f}h，{best.settlement_count} 次结算")
        print(f"  最差 Net Edge：{worst.net_edge_bps:+.1f} bps")
        print(f"    → {worst.exchange.upper()} {worst.symbol} @ {worst.start_dt.strftime('%Y-%m-%d %H:%M')} UTC")

    # 保存 JSON 结果
    result = {
        "analysis_params": {
            "extreme_funding_threshold_pct": EXTREME_FUNDING_THRESHOLD_PCT,
            "persistence_window": PERSISTENCE_WINDOW,
            "persistence_min": PERSISTENCE_MIN,
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
            "max_holding_hours": MAX_HOLDING_HOURS,
        },
        "summaries": [
            {
                "symbol": s.symbol,
                "exchange": s.exchange,
                "total_snapshots": s.total_snapshots,
                "date_range": list(s.date_range),
                "event_count": s.event_count,
                "profitable_event_count": s.profitable_event_count,
                "avg_net_edge_bps": round(s.avg_net_edge_bps, 2),
                "events": [
                    {
                        "start": ev.start_dt.isoformat(),
                        "end": ev.end_dt.isoformat(),
                        "duration_hours": round(ev.duration_hours, 1),
                        "peak_annualized_pct": round(ev.peak_annualized_pct, 2),
                        "avg_annualized_pct": round(ev.avg_annualized_pct, 2),
                        "avg_persistence": round(ev.avg_persistence, 3),
                        "settlement_count": ev.settlement_count,
                        "gross_funding_income_bps": ev.gross_funding_income_bps,
                        "net_edge_bps": ev.net_edge_bps,
                        "is_profitable": ev.is_profitable,
                    }
                    for ev in s.extreme_events
                ],
            }
            for s in all_summaries
        ],
    }

    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n  结构化结果已保存至：{OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    main()
