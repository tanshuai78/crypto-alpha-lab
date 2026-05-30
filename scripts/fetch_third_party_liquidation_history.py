from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any
import urllib.request
import urllib.parse
import urllib.error
import json

logger = logging.getLogger(__name__)


def symbol_to_coinalyze_contract(symbol: str) -> dict[str, Any]:
    # Mapping for symbols
    mapping = {
        "BTC/USDT": "BTCUSDT_PERP.A",
        "ETH/USDT": "ETHUSDT_PERP.A",
        "SOL/USDT": "SOLUSDT_PERP.A",
        "XRP/USDT": "XRPUSDT_PERP.A",
        "DOGE/USDT": "DOGEUSDT_PERP.A",
    }
    coinalyze_symbol = mapping.get(symbol)
    if not coinalyze_symbol:
        clean = symbol.replace("/", "")
        coinalyze_symbol = f"{clean}_PERP.A"

    parts = symbol.split("/")
    base = parts[0] if len(parts) > 0 else ""
    quote = parts[1] if len(parts) > 1 else ""

    return {
        "input_symbol": symbol,
        "coinalyze_symbol": coinalyze_symbol,
        "exchange": "binance",
        "symbol_on_exchange": coinalyze_symbol.split("_")[0] if "_" in coinalyze_symbol else coinalyze_symbol,
        "base_asset": base,
        "quote_asset": quote,
        "is_perpetual": True,
        "margined": "STABLE",
        "mapping_source": "supported_future_markets|static_fallback",
    }


def normalize_interval(interval: str) -> str:
    if interval in ("1h", "1hour"):
        return "1hour"
    return interval


def load_feasibility_audit() -> dict[str, Any]:
    # Check if API key is present in environment to decide api_access state
    api_key = os.environ.get("COINALYZE_API_KEY", "")
    api_access = "available" if api_key else "unavailable"

    return {
        "vendor_candidates": [
            {
                "vendor": "coinalyze",
                "api_access": api_access,
                "requires_paid_plan": False,
                "granularity": "1hour",
                "exchange_coverage": ["binance", "okx", "bybit"],
                "symbol_coverage": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
                "historical_depth_days": 80,
                "can_support_replay": True,
                "blocker": "" if api_key else "requires_coinalyze_api_key",
            }
        ]
    }


def fetch_historical_liquidations(
    symbol: str,
    from_ts_sec: int,
    to_ts_sec: int,
    interval: str = "1hour",
    api_key: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    if not api_key:
        api_key = os.environ.get("COINALYZE_API_KEY", "")
    if not api_key:
        logger.warning("COINALYZE_API_KEY missing from environment. Gracefully degrading to empty payload.")
        return [], "no_api_key"

    coinalyze_symbol_info = symbol_to_coinalyze_contract(symbol)
    coinalyze_symbol = coinalyze_symbol_info["coinalyze_symbol"]

    base_url = "https://api.coinalyze.net/v1/liquidation-history"
    params = {
        "symbols": coinalyze_symbol,
        "interval": normalize_interval(interval),
        "from": str(from_ts_sec),
        "to": str(to_ts_sec),
        "convert_to_usd": "true",
        "api_key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Antigravity/1.0"})
        with urllib.request.urlopen(req) as response:
            status_code = getattr(response, "getcode", lambda: 200)()
            if status_code == 200:
                data = json.loads(response.read().decode("utf-8"))
                if not data:
                    return [], "api_ok_empty_rows"
                return data, "api_ok_non_empty_rows"
            else:
                if status_code in (401, 403):
                    reason = "api_auth_failed"
                elif status_code == 429:
                    reason = "api_rate_limited"
                else:
                    reason = f"api_error_{status_code}"
                logger.error(f"Failed to fetch liquidations, status code: {status_code}")
                return [], reason
    except urllib.error.HTTPError as e:
        status_code = e.code
        if status_code in (401, 403):
            reason = "api_auth_failed"
        elif status_code == 429:
            reason = "api_rate_limited"
        else:
            reason = f"api_error_{status_code}"
        logger.error(f"HTTPError fetching from Coinalyze: {e}")
        return [], reason
    except Exception as e:
        logger.error(f"Error fetching historical liquidations from Coinalyze: {e}")
        return [], "api_error"


def normalize_coinalyze_payload(
    payload: list[dict[str, Any]] | None,
    symbol: str,
) -> list[dict[str, Any]]:
    if not payload:
        return []

    coinalyze_symbol_info = symbol_to_coinalyze_contract(symbol)
    coinalyze_symbol = coinalyze_symbol_info["coinalyze_symbol"]

    # We need to aggregate duplicate symbol + hour_bucket_ms rows by sum.
    aggregated: dict[int, dict[str, Any]] = {}

    history_rows: list[dict[str, Any]] = []
    for row in payload:
        if isinstance(row, dict) and isinstance(row.get("history"), list):
            history_rows.extend(
                item for item in row["history"] if isinstance(item, dict)
            )
        elif isinstance(row, dict):
            history_rows.append(row)

    for row in history_rows:
        t_value = row.get("t")
        if t_value in (None, ""):
            continue

        t_sec = int(t_value)
        hour_bucket_ms = t_sec * 1000

        long_liq = float(row.get("l") or 0.0)
        short_liq = float(row.get("s") or 0.0)

        if hour_bucket_ms not in aggregated:
            aggregated[hour_bucket_ms] = {
                "long": 0.0,
                "short": 0.0,
            }
        aggregated[hour_bucket_ms]["long"] += long_liq
        aggregated[hour_bucket_ms]["short"] += short_liq

    normalized: list[dict[str, Any]] = []
    for bucket_ms, vals in aggregated.items():
        dt = datetime.fromtimestamp(bucket_ms / 1000, tz=timezone.utc)
        hour_bucket_utc = dt.strftime("%Y-%m-%dT%H:00")

        long_liq = vals["long"]
        short_liq = vals["short"]
        total_liq = long_liq + short_liq

        normalized.append({
            "symbol": symbol,
            "vendor_symbol": coinalyze_symbol,
            "hour_bucket_ms": bucket_ms,
            "hour_bucket_utc": hour_bucket_utc,
            "long_liquidation_notional_1h_usdt": long_liq,
            "short_liquidation_notional_1h_usdt": short_liq,
            "total_liquidation_notional_1h_usdt": total_liq,
            "liquidation_notional_1h_usdt": total_liq,
            "liquidation_source": "third_party_historical",
            "liquidation_source_quality": "historical_vendor_dataset",
            "liquidation_notional_semantics": "vendor_reported_hourly_liquidation_notional",
            "vendor_name": "coinalyze",
            "vendor_granularity": "1hour",
            "normalized_granularity": "1h",
            "convert_to_usd": True,
            "timestamp_unit_source": "seconds",
        })

    return normalized


def build_route_b_hourly_summary(
    rows: list[dict[str, Any]],
    route_b_status: str | None = None,
    *,
    request_count: int = 0,
    requested_symbols: list[str] | None = None,
    interval: str = "1hour",
    from_ts_sec: int = 0,
    to_ts_sec: int = 0,
) -> dict[str, Any]:
    symbols = sorted(list(set(row["symbol"] for row in rows)))
    symbol_count = len(symbols)
    row_count = len(rows)
    requested_symbols = sorted(requested_symbols or [])
    
    if rows:
        start_ts = min(row["hour_bucket_ms"] for row in rows)
        end_ts = max(row["hour_bucket_ms"] for row in rows)
        time_span_hours = int((end_ts - start_ts) / 3600000)
    else:
        start_ts = 0
        end_ts = 0
        time_span_hours = 0
        
    rows_per_symbol = {}
    for row in rows:
        sym = row["symbol"]
        rows_per_symbol[sym] = rows_per_symbol.get(sym, 0) + 1
        
    if route_b_status is None:
        api_key = os.environ.get("COINALYZE_API_KEY", "")
        if not api_key:
            route_b_status = "no_api_key"
        elif row_count == 0:
            route_b_status = "api_ok_empty_rows"
        else:
            route_b_status = "api_ok_non_empty_rows"
            
    return {
        "vendor": "coinalyze",
        "route_b_status": route_b_status,
        "symbol_count": symbol_count,
        "symbols": symbols,
        "request_count": request_count,
        "requested_symbols": requested_symbols,
        "interval": normalize_interval(interval),
        "from_ts_sec": from_ts_sec,
        "to_ts_sec": to_ts_sec,
        "row_count": row_count,
        "start_timestamp_ms": start_ts,
        "end_timestamp_ms": end_ts,
        "time_span_hours": time_span_hours,
        "rows_per_symbol": rows_per_symbol,
        "coverage_quality": "historical_vendor_dataset",
        "deduplicated_rows_count": row_count,
        "convert_to_usd": True,
        "vendor_granularity": "1hour",
        "normalized_granularity": "1h",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description="Fetch third party liquidation history from Coinalyze.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Space-separated list of symbols (or comma-separated list as a single arg)",
    )
    parser.add_argument("--interval", default="1hour", help="Granularity interval, default 1hour")
    parser.add_argument("--lookback-hours", type=int, default=1500, help="Lookback duration in hours")
    parser.add_argument("--output-jsonl", help="Output path for JSONL formatted rows")
    parser.add_argument("--summary-output", help="Output path for the hourly summary report")
    parser.add_argument("--feasibility-output", help="Output path for the feasibility report")
    
    args = parser.parse_args(argv)
    
    # Process symbols
    symbols = []
    if args.symbols:
        for s_arg in args.symbols:
            if "," in s_arg:
                symbols.extend(s.strip() for s in s_arg.split(",") if s.strip())
            else:
                symbols.append(s_arg.strip())
    else:
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
        
    # Calculate time window
    to_ts_sec = int(time.time())
    from_ts_sec = to_ts_sec - (args.lookback_hours * 3600)
    
    symbol_statuses = []
    all_normalized_rows = []
    
    api_key = os.environ.get("COINALYZE_API_KEY", "")
    
    if not api_key:
        symbol_statuses.append("no_api_key")
    else:
        for idx, symbol in enumerate(symbols):
            if idx > 0:
                time.sleep(1.0)
                
            logger.info(f"Fetching liquidation history for {symbol}...")
            try:
                payload, status = fetch_historical_liquidations(
                    symbol=symbol,
                    from_ts_sec=from_ts_sec,
                    to_ts_sec=to_ts_sec,
                    interval=args.interval,
                    api_key=api_key
                )
                symbol_statuses.append(status)
                
                if payload:
                    normalized = normalize_coinalyze_payload(payload, symbol=symbol)
                    all_normalized_rows.extend(normalized)
            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                symbol_statuses.append("api_error")
                
    # Resolve the final route_b_status
    if not api_key:
        final_status = "no_api_key"
    elif any(s == "api_auth_failed" for s in symbol_statuses):
        final_status = "api_auth_failed"
    elif any(s == "api_rate_limited" for s in symbol_statuses):
        final_status = "api_rate_limited"
    elif any(s == "api_ok_non_empty_rows" for s in symbol_statuses):
        final_status = "api_ok_non_empty_rows"
    else:
        final_status = "api_ok_empty_rows"
        
    summary = build_route_b_hourly_summary(
        all_normalized_rows,
        route_b_status=final_status,
        request_count=len(symbols),
        requested_symbols=symbols,
        interval=args.interval,
        from_ts_sec=from_ts_sec,
        to_ts_sec=to_ts_sec,
    )
    summary["symbol_count"] = len(symbols)
    summary["symbols"] = sorted(symbols)
    
    feasibility = load_feasibility_audit()
    if "vendor_candidates" in feasibility:
        for candidate in feasibility["vendor_candidates"]:
            if candidate["vendor"] == "coinalyze":
                candidate["route_b_status"] = final_status
                candidate["historical_depth_days"] = args.lookback_hours // 24
    feasibility.update({
        "request_count": len(symbols),
        "requested_symbols": sorted(symbols),
        "interval": normalize_interval(args.interval),
        "from_ts_sec": from_ts_sec,
        "to_ts_sec": to_ts_sec,
    })
                
    if args.output_jsonl:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_jsonl)), exist_ok=True)
        sorted_rows = sorted(all_normalized_rows, key=lambda x: (x["symbol"], x["hour_bucket_ms"]))
        with open(args.output_jsonl, "w") as f:
            for row in sorted_rows:
                f.write(json.dumps(row) + "\n")
        logger.info(f"Saved normalized rows to {args.output_jsonl}")
        
    if args.summary_output:
        os.makedirs(os.path.dirname(os.path.abspath(args.summary_output)), exist_ok=True)
        with open(args.summary_output, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved summary report to {args.summary_output}")
        
    if args.feasibility_output:
        os.makedirs(os.path.dirname(os.path.abspath(args.feasibility_output)), exist_ok=True)
        with open(args.feasibility_output, "w") as f:
            json.dump(feasibility, f, indent=2)
        logger.info(f"Saved feasibility report to {args.feasibility_output}")
        
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
