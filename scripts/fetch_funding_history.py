"""
scripts/fetch_funding_history.py
----------------------------------
从 Binance 公开 API 拉取 BTC/ETH/SOL/XRP/ADA/DOGE 的完整历史结算费率
（真实结算值，非预测值，无限幅，无需 API Key）

接口：GET https://fapi.binance.com/fapi/v1/fundingRate
- 每 8 小时一次结算
- 用 startTime 正向分页，limit=1000 每页约 333 天
- 从 START_DATE 推进到当前

运行方式：
    cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
    uv run python scripts/fetch_funding_history.py

输出：
    data/funding_settled/binance_{SYMBOL}_settled.jsonl
    每行一条结算记录，格式：
    {"symbol": "BTC/USDT", "funding_time_ms": ..., "funding_rate": ..., "mark_price": ..., "annualized_pct": ...}
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ─── 配置 ──────────────────────────────────────────────────────────────────────

BASE_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
PROXY = None  # 如需代理，设为 "http://127.0.0.1:7890"

# 拉取起始时间（2021-01-01 UTC 00:00:00）
START_DATE = datetime(2021, 1, 1, tzinfo=timezone.utc)
START_TIME_MS = int(START_DATE.timestamp() * 1000)

# 目标 Symbol（Binance 合约格式 → 统一格式）
SYMBOLS = {
    "BTCUSDT":  "BTC/USDT",
    "ETHUSDT":  "ETH/USDT",
    "SOLUSDT":  "SOL/USDT",
    "XRPUSDT":  "XRP/USDT",
    "ADAUSDT":  "ADA/USDT",
    "DOGEUSDT": "DOGE/USDT",
}

SETTLEMENTS_PER_DAY = 3
ANN_MULT = SETTLEMENTS_PER_DAY * 365  # 1095

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "funding_settled"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LIMIT = 1000            # 每次请求最大条数（约覆盖 333 天）
SLEEP_BETWEEN_REQ = 0.4 # 秒，避免触发限频

# ─── HTTP 工具 ──────────────────────────────────────────────────────────────────

def _get(url: str) -> bytes:
    if PROXY:
        proxy_handler = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()
    req = urllib.request.Request(url, headers={"User-Agent": "crypto-alpha-lab/1.0"})
    with opener.open(req, timeout=20) as resp:
        return resp.read()


# ─── 核心函数 ──────────────────────────────────────────────────────────────────

def fetch_batch(symbol: str, start_time_ms: int) -> list[dict]:
    """拉取 symbol 在 start_time_ms 之后的最多 LIMIT 条结算记录（升序）"""
    params = {
        "symbol": symbol,
        "startTime": str(start_time_ms),
        "limit": str(LIMIT),
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    data = json.loads(_get(url).decode())
    return data if isinstance(data, list) else []


def fetch_all(binance_sym: str, unified_sym: str) -> list[dict]:
    """
    用 startTime 正向分页，拉取从 START_TIME_MS 至今的全部结算记录。
    Binance API 每次返回从 startTime 开始的 limit 条（升序）。
    用最后一条的 fundingTime + 1ms 作为下一页的 startTime。
    """
    all_records: list[dict] = []
    cur_start_ms = START_TIME_MS
    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    page = 0

    print(f"\n  拉取 {unified_sym} ...", end="", flush=True)

    while cur_start_ms <= now_ms:
        try:
            batch = fetch_batch(binance_sym, cur_start_ms)
        except Exception as e:
            print(f"\n  [WARN] 请求失败: {e}，重试...", end="", flush=True)
            time.sleep(2)
            try:
                batch = fetch_batch(binance_sym, cur_start_ms)
            except Exception as e2:
                print(f"\n  [ERROR] 重试失败: {e2}，跳过")
                break

        if not batch:
            break

        for rec in batch:
            fr = float(rec["fundingRate"])
            ann = fr * ANN_MULT * 100
            # 早期记录 markPrice 字段可能为空字符串
            raw_mp = rec.get("markPrice") or ""
            mark_price = float(raw_mp) if raw_mp else 0.0
            all_records.append({
                "symbol": unified_sym,
                "funding_time_ms": int(rec["fundingTime"]),
                "funding_rate": fr,
                "mark_price": mark_price,
                "annualized_pct": round(ann, 4),
            })

        page += 1
        print(f" {page}", end="", flush=True)

        # 下一页从最后一条的时间 + 1ms 开始
        last_ts = int(batch[-1]["fundingTime"])
        cur_start_ms = last_ts + 1

        # 如果本页不足 limit 条，说明已到末尾
        if len(batch) < LIMIT:
            break

        time.sleep(SLEEP_BETWEEN_REQ)

    return all_records


def save(binance_sym: str, records: list[dict]) -> Path:
    """写入 JSONL 文件"""
    outfile = OUTPUT_DIR / f"binance_{binance_sym}_settled.jsonl"
    with open(outfile, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return outfile


# ─── 主流程 ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Binance 历史结算费率下载器")
    print(f"  时间范围：{START_DATE.strftime('%Y-%m-%d')} UTC → 今日")
    print(f"  输出目录：{OUTPUT_DIR}")
    print("=" * 60)

    summary = []
    for binance_sym, unified_sym in SYMBOLS.items():
        records = fetch_all(binance_sym, unified_sym)
        if not records:
            print(f"\n  [SKIP] {unified_sym}: 无数据返回")
            continue

        outfile = save(binance_sym, records)
        first_dt = datetime.fromtimestamp(records[0]["funding_time_ms"] / 1000, tz=timezone.utc)
        last_dt  = datetime.fromtimestamp(records[-1]["funding_time_ms"] / 1000, tz=timezone.utc)

        ann_vals = [r["annualized_pct"] for r in records]
        above_30  = sum(1 for v in ann_vals if v > 30)
        above_50  = sum(1 for v in ann_vals if v > 50)
        above_100 = sum(1 for v in ann_vals if v > 100)
        below_m30 = sum(1 for v in ann_vals if v < -30)
        max_ann   = max(ann_vals)
        min_ann   = min(ann_vals)

        print(f"\n  ✅ {unified_sym}  {len(records):,} 条结算记录")
        print(f"     范围：{first_dt.strftime('%Y-%m-%d')} → {last_dt.strftime('%Y-%m-%d')}")
        print(f"     最高年化：{max_ann:+.1f}%  最低：{min_ann:+.1f}%")
        print(f"     > 30% ann: {above_30} 次 ({above_30/len(records):.1%})")
        print(f"     > 50% ann: {above_50} 次 ({above_50/len(records):.1%})")
        print(f"     > 100% ann: {above_100} 次 ({above_100/len(records):.1%})")
        print(f"     < -30% ann: {below_m30} 次 ({below_m30/len(records):.1%})")
        print(f"     → 保存至：{outfile.name}")

        summary.append({
            "symbol": unified_sym,
            "records": len(records),
            "date_from": first_dt.strftime("%Y-%m-%d"),
            "date_to": last_dt.strftime("%Y-%m-%d"),
            "max_annualized_pct": round(max_ann, 2),
            "min_annualized_pct": round(min_ann, 2),
            "above_30_count": above_30,
            "above_50_count": above_50,
            "above_100_count": above_100,
            "below_minus30_count": below_m30,
        })

    summary_file = OUTPUT_DIR / "download_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"\n{'='*60}")
    print(f"  下载完成，汇总保存至：{summary_file}")
    print()


if __name__ == "__main__":
    main()
