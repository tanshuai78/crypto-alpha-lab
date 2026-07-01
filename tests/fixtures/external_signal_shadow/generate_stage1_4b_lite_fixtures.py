import json
from pathlib import Path


def generate_fixtures():
    # Base timestamp: 1781165400000 ms (approximately 2026-06-12)
    base_time = 1781165400000
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

    # 1. Generate funding rate history (spaced by 8 hours = 28,800,000 ms)
    # We generate 100 history points per symbol so that the min_funding_history_points >= 30 check passes
    funding_rows = []
    for symbol in symbols:
        for i in range(100):
            # To ensure the percentile is 90% or above when we want it to trigger, or general values
            rate = 0.0001
            if i % 10 == 0:
                rate = 0.0003 # high value
            elif i % 10 == 1:
                rate = -0.0001 # low value
            funding_rows.append({
                "symbol": symbol,
                "fundingTime": base_time - (100 - i) * 8 * 3600 * 1000,
                "fundingRate": rate
            })

    # 2. Generate 15m price bars (spaced by 15 minutes = 900,000 ms)
    # We generate 200 bars per symbol, covering the base time forward and backward
    price_rows = []
    for symbol in symbols:
        for i in range(200):
            t = base_time + (i - 100) * 900000
            # Let's put a trigger pattern at i = 120 (which is base_time + 20 * 900000)
            # For "oi_expansion_trend_confirmation" long event, we need price_4h_return_pct >= 1.5%
            # Price at T120 (base_time + 20 * 15m): let's make it climb
            close = 50000.0
            if i >= 120:
                # 4h return (16 bars ago was T104)
                # T104 price = 50000.0, T120 price = 51000.0 (+2.0% return)
                close = 51000.0
            price_rows.append({
                "symbol": symbol,
                "bar_start_ms": t,
                "close_price": close,
                "quote_volume": 1000000.0
            })

    # 3. Generate OI rows (spaced by 1 hour = 3,600,000 ms)
    # We can also space them by 15m to match price bar times
    oi_rows = []
    for symbol in symbols:
        for i in range(200):
            t = base_time + (i - 100) * 900000
            # For "oi_expansion_trend_confirmation" long event, we need oi_4h_change_pct >= 2.0%
            # T104 (16 bars ago) OI = 100.0, T120 OI = 103.0 (+3.0%)
            oi = 100.0
            if i >= 120:
                oi = 103.0
            oi_rows.append({
                "symbol": symbol,
                "timestamp_ms": t,
                "sumOpenInterest": oi
            })

    output_dir = Path("/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/tests/fixtures/external_signal_shadow")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "stage1_4b_lite_funding_rows.json", "w", encoding="utf-8") as f:
        json.dump(funding_rows, f, indent=2, ensure_ascii=False)

    with open(output_dir / "stage1_4b_lite_oi_rows.json", "w", encoding="utf-8") as f:
        json.dump(oi_rows, f, indent=2, ensure_ascii=False)

    with open(output_dir / "stage1_4b_lite_price_rows.json", "w", encoding="utf-8") as f:
        json.dump(price_rows, f, indent=2, ensure_ascii=False)

    print("Successfully generated all stage1_4b_lite fixture JSON files.")

if __name__ == "__main__":
    generate_fixtures()
