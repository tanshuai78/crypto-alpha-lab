import json
import os


def _load_raw_rows(path: str) -> list:
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
                raise ValueError(f"Failed to parse JSON at line {line_num}: {e}")
    return rows


def load_funding_rows(path: str) -> list[dict]:
    raw = _load_raw_rows(path)
    normalized = []
    for idx, r in enumerate(raw):
        if not isinstance(r, dict):
            raise ValueError(f"Funding row at index {idx} is not a dict: {r}")

        symbol = r.get("symbol") or r.get("s")
        if symbol is None:
            raise ValueError(f"Missing symbol in funding row at index {idx}: {r}")

        ft_val = None
        for k in ("fundingTime", "timestamp", "time", "t"):
            if r.get(k) is not None:
                ft_val = r[k]
                break
        if ft_val is None:
            raise ValueError(f"Missing fundingTime in funding row at index {idx}: {r}")
        try:
            fundingTime = int(ft_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid fundingTime in funding row at index {idx}: {ft_val}. Error: {e}")

        fr_val = None
        for k in ("fundingRate", "rate", "r"):
            if r.get(k) is not None:
                fr_val = r[k]
                break
        if fr_val is None:
            raise ValueError(f"Missing fundingRate in funding row at index {idx}: {r}")
        try:
            fundingRate = float(fr_val)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid fundingRate in funding row at index {idx}: {fr_val}. Error: {e}")

        normalized.append({
            "symbol": str(symbol),
            "fundingTime": fundingTime,
            "fundingRate": fundingRate,
        })
    return normalized


def load_oi_rows(path: str) -> list[dict]:
    raw = _load_raw_rows(path)
    normalized = []
    for idx, r in enumerate(raw):
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

        normalized.append({
            "symbol": str(symbol),
            "timestamp_ms": timestamp_ms,
            "sumOpenInterest": sumOpenInterest,
        })
    return normalized


def load_price_rows(path: str, default_symbol: str = None) -> list[dict]:
    if not os.path.exists(path):
        raise ValueError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if content.startswith("{"):
        try:
            data = json.loads(content)
            is_symbol_mapping = True
            for k, v in data.items():
                if k in ("symbol", "s", "bar_start_ms", "open_time", "close", "close_price", "c"):
                    is_symbol_mapping = False
                    break
                if not isinstance(v, list):
                    is_symbol_mapping = False
                    break

            if is_symbol_mapping:
                normalized = []
                for symbol, rows in data.items():
                    for idx, r in enumerate(rows):
                        if isinstance(r, list | tuple):
                            if len(r) < 5:
                                raise ValueError(f"Price list row for {symbol} at index {idx} has length < 5: {r}")
                            try:
                                bar_start_ms = int(r[0])
                            except (TypeError, ValueError) as e:
                                raise ValueError(f"Invalid open_time in price list for {symbol} at index {idx}: {r[0]}. Error: {e}")
                            try:
                                open_price = float(r[1])
                            except (TypeError, ValueError, IndexError) as e:
                                raise ValueError(f"Invalid open price in price list for {symbol} at index {idx}: {r[1] if len(r) > 1 else None}. Error: {e}")
                            try:
                                close_price = float(r[4])
                            except (TypeError, ValueError) as e:
                                raise ValueError(f"Invalid close price in price list for {symbol} at index {idx}: {r[4]}. Error: {e}")
                            quote_volume = 0.0
                            if len(r) >= 6:
                                try:
                                    quote_volume = float(r[5])
                                except (TypeError, ValueError) as e:
                                    raise ValueError(f"Invalid volume in price list for {symbol} at index {idx}: {r[5]}. Error: {e}")
                            normalized.append({
                                "symbol": symbol,
                                "bar_start_ms": bar_start_ms,
                                "open_price": open_price,
                                "close_price": close_price,
                                "quote_volume": quote_volume,
                            })
                        elif isinstance(r, dict):
                            row_symbol = r.get("symbol") or r.get("s") or symbol
                            ts_val = None
                            for k_field in ("bar_start_ms", "open_time", "time", "t", "timestamp"):
                                if r.get(k_field) is not None:
                                    ts_val = r[k_field]
                                    break
                            if ts_val is None:
                                raise ValueError(f"Missing bar_start_ms in price dict for {symbol} at index {idx}: {r}")
                            bar_start_ms = int(ts_val)

                            o_val = None
                            for k_field in ("open_price", "open", "o"):
                                if r.get(k_field) is not None:
                                    o_val = r[k_field]
                                    break
                            if o_val is None:
                                raise ValueError(f"Missing open_price in price dict for {symbol} at index {idx}: {r}")
                            open_price = float(o_val)

                            c_val = None
                            for k_field in ("close_price", "close", "c"):
                                if r.get(k_field) is not None:
                                    c_val = r[k_field]
                                    break
                            if c_val is None:
                                raise ValueError(f"Missing close_price in price dict for {symbol} at index {idx}: {r}")
                            close_price = float(c_val)

                            q_val = 0.0
                            for k_field in ("quote_volume", "volume", "v", "quoteVolume", "q"):
                                if r.get(k_field) is not None:
                                    q_val = r[k_field]
                                    break
                            quote_volume = float(q_val)

                            normalized.append({
                                "symbol": row_symbol,
                                "bar_start_ms": bar_start_ms,
                                "open_price": open_price,
                                "close_price": close_price,
                                "quote_volume": quote_volume,
                            })
                return normalized
        except json.JSONDecodeError:
            pass

    raw = _load_raw_rows(path)
    normalized = []
    for idx, r in enumerate(raw):
        if isinstance(r, list | tuple):
            if len(r) < 5:
                raise ValueError(f"Price list row at index {idx} has length < 5: {r}")
            symbol = default_symbol
            if symbol is None:
                raise ValueError(f"Symbol not provided for list-format price row at index {idx}: {r}")
            try:
                bar_start_ms = int(r[0])
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid open_time in price list at index {idx}: {r[0]}. Error: {e}")
            try:
                open_price = float(r[1])
            except (TypeError, ValueError, IndexError) as e:
                raise ValueError(f"Invalid open price in price list at index {idx}: {r[1] if len(r) > 1 else None}. Error: {e}")
            try:
                close_price = float(r[4])
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid close price in price list at index {idx}: {r[4]}. Error: {e}")
            quote_volume = 0.0
            if len(r) >= 6:
                try:
                    quote_volume = float(r[5])
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Invalid volume in price list at index {idx}: {r[5]}. Error: {e}")
        elif isinstance(r, dict):
            symbol = r.get("symbol") or r.get("s") or default_symbol
            if symbol is None:
                raise ValueError(f"Missing symbol in price dict at index {idx}: {r}")

            ts_val = None
            for k in ("bar_start_ms", "open_time", "time", "t", "timestamp"):
                if r.get(k) is not None:
                    ts_val = r[k]
                    break
            if ts_val is None:
                raise ValueError(f"Missing bar_start_ms in price dict at index {idx}: {r}")
            try:
                bar_start_ms = int(ts_val)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid bar_start_ms in price dict at index {idx}: {ts_val}. Error: {e}")

            o_val = None
            for k in ("open_price", "open", "o"):
                if r.get(k) is not None:
                    o_val = r[k]
                    break

            c_val = None
            for k in ("close_price", "close", "c"):
                if r.get(k) is not None:
                    c_val = r[k]
                    break
            if c_val is None:
                raise ValueError(f"Missing close_price in price dict at index {idx}: {r}")
            try:
                close_price = float(c_val)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid close_price in price dict at index {idx}: {c_val}. Error: {e}")

            if o_val is None:
                open_price = close_price
            else:
                try:
                    open_price = float(o_val)
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Invalid open_price in price dict at index {idx}: {o_val}. Error: {e}")

            q_val = 0.0
            for k in ("quote_volume", "volume", "v", "quoteVolume", "q"):
                if r.get(k) is not None:
                    q_val = r[k]
                    break
            try:
                quote_volume = float(q_val)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid quote_volume in price dict at index {idx}: {q_val}. Error: {e}")
        else:
            raise ValueError(f"Price row at index {idx} is neither list nor dict: {r}")

        normalized.append({
            "symbol": str(symbol),
            "bar_start_ms": bar_start_ms,
            "open_price": open_price,
            "close_price": close_price,
            "quote_volume": quote_volume,
        })
    return normalized
