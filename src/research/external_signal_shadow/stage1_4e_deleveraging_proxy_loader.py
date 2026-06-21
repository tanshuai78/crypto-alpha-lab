import glob
import json
import os
from typing import Iterable, Sequence


def get_data_source_semantics() -> dict:
    return {
        "oi_source": "binance_vision_metrics",
        "oi_source_quality": "exchange_reported_hourly_snapshot",
        "price_source": "binance_kline_normalized",
        "price_source_quality": "close_price_proxy_not_fill_price",
        "funding_source": "binance_settled_funding_rate",
        "funding_source_quality": "settled_rate_not_realtime_prediction"
    }

def _load_single_file(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    # Try parsing as JSON first
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("[") or content.startswith("{"):
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return [data]
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass

    # Try parsing line-by-line JSONL
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse JSON at line {line_num} in {path}: {e}")
    return rows

def load_json_or_jsonl_paths(paths_or_globs: Sequence[str]) -> list[dict]:
    all_rows = []
    for pg in paths_or_globs:
        matched = glob.glob(pg)
        if not matched:
            # If glob doesn't match but pg is a direct file path that exists, try loading it
            if os.path.exists(pg):
                matched = [pg]
            else:
                raise ValueError(f"No files matched path/glob: {pg}")
        for path in matched:
            rows = _load_single_file(path)
            # Add file path context to raw rows if needed
            for r in rows:
                if isinstance(r, dict):
                    r["source_file"] = os.path.basename(path)
            all_rows.extend(rows)
    return all_rows

def normalize_oi_rows(rows: Iterable[dict]) -> list[dict]:
    normalized = []
    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            raise ValueError(f"OI row at index {idx} is not a dict: {r}")

        symbol = r.get("symbol") or r.get("s")
        if symbol is None:
            raise ValueError(f"Missing symbol in OI row at index {idx}: {r}")

        ts_val = None
        for k in ("timestamp_ms", "timestamp", "time", "t"):
            if r.get(k) is not None:
                ts_val = r[k]
                break
        if ts_val is None:
            raise ValueError(f"Missing timestamp in OI row at index {idx}: {r}")
        try:
            timestamp_ms = int(ts_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid timestamp in OI row at index {idx}: {ts_val}. Error: {e}")

        oi_val = None
        for k in ("sumOpenInterest", "openInterest", "oi"):
            if r.get(k) is not None:
                oi_val = r[k]
                break
        if oi_val is None:
            raise ValueError(f"Missing sumOpenInterest in OI row at index {idx}: {r}")
        try:
            sumOpenInterest = float(oi_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid sumOpenInterest in OI row at index {idx}: {oi_val}. Error: {e}")

        oi_val_value = None
        for k in ("sumOpenInterestValue", "openInterestValue", "oiv", "value"):
            if r.get(k) is not None:
                oi_val_value = r[k]
                break
        sumOpenInterestValue = 0.0
        if oi_val_value is not None:
            try:
                sumOpenInterestValue = float(oi_val_value)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid sumOpenInterestValue in OI row at index {idx}: {oi_val_value}. Error: {e}")

        normalized.append({
            "symbol": str(symbol),
            "timestamp_ms": timestamp_ms,
            "sumOpenInterest": sumOpenInterest,
            "sumOpenInterestValue": sumOpenInterestValue,
            "source": "binance_vision_metrics",
            "source_file": r.get("source_file", "")
        })
    return normalized

def normalize_price_rows(rows: Iterable[dict]) -> list[dict]:
    normalized = []
    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            raise ValueError(f"Price row at index {idx} is not a dict: {r}")

        symbol = r.get("symbol") or r.get("s")
        if symbol is None:
            raise ValueError(f"Missing symbol in Price row at index {idx}: {r}")

        ts_val = None
        for k in ("bar_start_ms", "open_time", "time", "timestamp", "t"):
            if r.get(k) is not None:
                ts_val = r[k]
                break
        if ts_val is None:
            raise ValueError(f"Missing bar_start_ms in Price row at index {idx}: {r}")
        try:
            bar_start_ms = int(ts_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid bar_start_ms in Price row at index {idx}: {ts_val}. Error: {e}")

        # Normalize open, high, low, close
        o_val = None
        for k in ("open", "open_price", "o"):
            if r.get(k) is not None:
                o_val = r[k]
                break
        if o_val is None:
            raise ValueError(f"Missing open price in Price row at index {idx}: {r}")
        open_price = float(o_val)

        c_val = None
        for k in ("close", "close_price", "c"):
            if r.get(k) is not None:
                c_val = r[k]
                break
        if c_val is None:
            raise ValueError(f"Missing close price in Price row at index {idx}: {r}")
        close_price = float(c_val)

        h_val = None
        for k in ("high", "high_price", "h"):
            if r.get(k) is not None:
                h_val = r[k]
                break
        high_price = float(h_val) if h_val is not None else max(open_price, close_price)

        l_val = None
        for k in ("low", "low_price", "l"):
            if r.get(k) is not None:
                l_val = r[k]
                break
        low_price = float(l_val) if l_val is not None else min(open_price, close_price)


        q_vol = 0.0
        for k in ("quote_volume", "volume", "v", "quoteVolume"):
            if r.get(k) is not None:
                q_vol = r[k]
                break
        quote_volume = float(q_vol) if q_vol is not None else 0.0

        normalized.append({
            "symbol": str(symbol),
            "bar_start_ms": bar_start_ms,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "quote_volume": quote_volume
        })
    return normalized

def normalize_funding_rows(rows: Iterable[dict]) -> list[dict]:
    normalized = []
    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            raise ValueError(f"Funding row at index {idx} is not a dict: {r}")

        symbol = r.get("symbol") or r.get("s")
        if symbol is None:
            raise ValueError(f"Missing symbol in Funding row at index {idx}: {r}")

        ft_val = None
        for k in ("funding_time_ms", "fundingTime", "timestamp", "time", "t"):
            if r.get(k) is not None:
                ft_val = r[k]
                break
        if ft_val is None:
            raise ValueError(f"Missing fundingTime in Funding row at index {idx}: {r}")
        try:
            funding_time_ms = int(ft_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid fundingTime in Funding row at index {idx}: {ft_val}. Error: {e}")

        fr_val = None
        for k in ("funding_rate", "fundingRate", "rate", "r"):
            if r.get(k) is not None:
                fr_val = r[k]
                break
        if fr_val is None:
            raise ValueError(f"Missing fundingRate in Funding row at index {idx}: {r}")
        try:
            funding_rate = float(fr_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid fundingRate in Funding row at index {idx}: {fr_val}. Error: {e}")

        normalized.append({
            "symbol": str(symbol),
            "funding_time_ms": funding_time_ms,
            "funding_rate": funding_rate
        })
    return normalized
