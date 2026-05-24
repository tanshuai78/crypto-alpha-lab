# Extreme Funding Watchlist Server Operation

## Purpose

Run Phase 1A.5 in observation-only mode. This daemon reads only Binance public endpoints and emits watchlist events, heartbeats, reject summaries, and JSONL evidence. It must not read private keys, balances, or execution state.

## Local One-Shot Dry Run

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --once
```

Expected:

- Process exits after one polling pass.
- No private API key required.
- JSONL evidence is written under `data/extreme_funding_watch_events.jsonl`.
- No imports from `execution`.

## Local Bounded Dry Run

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --max-iterations 3
```

Expected:

- Process exits after 3 iterations.
- OI is fetched through a 60s cache, not every 10s loop.
- Watch events may remain absent during the 5-minute persistence warm-up.

## Server Run Command

```bash
PYTHONPATH=src uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
```

## systemd Example

```ini
[Unit]
Description=crypto-alpha-lab extreme funding watchlist
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/crypto-alpha-lab
Environment=PYTHONPATH=src
ExecStart=/usr/bin/env uv run python scripts/run_extreme_funding_watchlist.py --forever --data-root data
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 24h Review Checklist

- Total iterations.
- `watchlist_http_error`, `watchlist_url_error`, `watchlist_json_error`, `watchlist_schema_error` counts.
- `api_stale` count.
- `missing_premium` count.
- `micro_persistence_warmup` count.
- `watch_level_1/2/3` event count.
- Symbols that triggered events.
- Whether `oi_status` is mostly `ok`, `missing`, or `stale`.
- JSONL file size and latest heartbeat timestamp.

## Safety Boundary

This daemon is not allowed to:

- Import `execution`.
- Emit `SignalCandidate`.
- Create `TradeIntent`.
- Read API keys.
- Place orders.
