"""
configs/base.py — Single source of truth for all configuration constants.

Rules:
- No magic numbers anywhere in src/. All thresholds must come from here.
- Add a comment for every constant explaining its meaning and safe range.
- Keep sections grouped by module.
"""

# ─── Exchange Connectivity ─────────────────────────────────────────────────────

EXCHANGE_TIMEOUT_MS = 10_000
# Network timeout per request. 10s is conservative for most VPS setups.
# Reduce to 5000 on fast connections, increase to 15000 on mobile/unstable networks.

EXCHANGES: dict = {
    # Format: exchange_id -> ccxt config dict
    # Populate with your API keys via environment variables or a local secrets file.
    # Example (DO NOT commit real keys):
    # "binance": {
    #     "id": "binance",
    #     "apiKey": os.environ["BINANCE_API_KEY"],
    #     "secret": os.environ["BINANCE_SECRET"],
    #     "options": {"defaultType": "spot"},
    # },
    # "okx": {
    #     "id": "okx",
    #     "apiKey": os.environ["OKX_API_KEY"],
    #     "secret": os.environ["OKX_SECRET"],
    #     "password": os.environ["OKX_PASSPHRASE"],
    #     "hostname": "aws.okx.com",   # Use AWS endpoint to reduce latency
    #     "proxy": "http://127.0.0.1:7890",  # If behind proxy
    #     "options": {"defaultType": "swap"},
    # },
}

# ─── Execution Engine ──────────────────────────────────────────────────────────

EXECUTION_JOURNAL_PATH = "data/execution_journal.db"
# SQLite journal for all execution events. Relative to project root.

EXECUTION_DUST_FILL_RATIO = 0.005
# If hedge leg fill ratio vs maker leg is within this fraction, treat as "dust" (acceptable residual).
# 0.005 = 0.5% of position size. Prevents unnecessary rollbacks on tiny rounding differences.

EXECUTION_DUST_NOTIONAL_THRESHOLD_USDT = 5.0
# Maximum residual notional (in USDT) that qualifies as "dust". Even if ratio is satisfied,
# any residual above this triggers rollback consideration.

EXECUTION_UNKNOWN_REMOTE_MAX_AGE_SEC = 10.0
# How long to keep retrying client_order_id lookup after a maker timeout before giving up.
# 10s is enough for most exchanges to propagate order state.

EXECUTION_UNKNOWN_REMOTE_RETRY_DELAYS_SEC = (1.0, 2.0, 4.0)
# Retry intervals (seconds) when polling for unknown remote state.
# Total max wait = sum(delays) + EXECUTION_UNKNOWN_REMOTE_MAX_AGE_SEC.

# ─── Inventory Guard ──────────────────────────────────────────────────────────

INVENTORY_GUARD_WARNING_RATIO = 0.05
# net_delta / gross_exposure ratio that triggers a WARNING log. No action yet.
# 0.05 = 5% imbalance. Expect this occasionally due to rounding.

INVENTORY_GUARD_PAUSE_RATIO = 0.10
# Ratio that pauses new position entries. Existing positions unaffected.
# 0.10 = 10% imbalance. Indicates a partial fill that wasn't fully hedged.

INVENTORY_GUARD_FORCE_DELEVERAGE_RATIO = 0.20
# Ratio that triggers forced deleveraging + recovery lock.
# 0.20 = 20% imbalance. Indicates a significant one-sided exposure.
# Recovery lock only clears after N consecutive healthy assessments + zero orphan intents.

# ─── Risk Limits ──────────────────────────────────────────────────────────────

RISK_MAX_SINGLE_POSITION_USDT = 500.0
# Hard cap on any single trade's notional exposure (per our discussion: 5k-50k capital scale).
# Do NOT increase this without re-validating strategy edge at the new size.

RISK_MAX_CONCURRENT_POSITIONS = 2
# Maximum number of simultaneously open positions across all strategies.

RISK_EQUITY_CURVE_DRAWDOWN_HALT_PCT = 0.05
# If equity drops more than 5% from its recent peak, halt all new entries.
# This is the outer circuit breaker — not a per-trade stop.

RISK_LIVE_TRADING_ENABLED = False
# MASTER SWITCH. Must be explicitly set to True per strategy after shadow validation.
# Default is False. The system boots in observation-only mode.

# ─── Market Data ──────────────────────────────────────────────────────────────

MARKET_DATA_MIN_24H_VOLUME_USDT = 10_000_000.0
# Minimum 24h spot volume to consider a symbol. Filters out illiquid pairs.
# 10M USDT is conservative for BTC/ETH majors. May need lowering for small-cap strategies.

MARKET_DATA_FETCH_RETRY_DELAY_SEC = 1.0
# Delay between fetch retries on retryable errors (rate limit, network hiccup).

# ─── Strategy: Extreme Funding Event Scanner ─────────────────────────────────

EXTREME_FUNDING_ANNUALIZED_THRESHOLD_PCT = 30.0
# Minimum annualized funding rate (%) to trigger an extreme funding event signal.
# 30% annualized = ~0.083% per 8h settlement. This is roughly 6x the typical BTC rate.

EXTREME_FUNDING_MIN_PERSISTENCE = 0.7
# Minimum funding persistence required (fraction of recent settlements that were positive).
# 0.7 = 70% of the last N settlements were positive. Avoids single-spike false signals.

EXTREME_FUNDING_MAX_HOLDING_HOURS = 24
# Maximum holding period for an extreme funding position (hours).
# Exit at next settlement cycle or when funding drops below threshold.

# ─── Strategy: Trend / Liquidation Regime ────────────────────────────────────

TREND_REGIME_VOL_BREAKOUT_MULTIPLIER = 2.0
# Current 1h volatility must exceed N × 30-day baseline to qualify as a vol breakout.

TREND_REGIME_MAX_HOLDING_HOURS = 48
# Maximum holding period. Directional positions must have a hard time limit.

TREND_REGIME_STOP_LOSS_PCT = 2.0
# Per-trade stop loss in percent of entry price. Hard stop, not trailing.

# ─── Strategy: Long-Horizon Funding Basis Desk ───────────────────────────────

BASIS_DESK_MAX_HOLDING_DAYS = 7
# Maximum holding period for a basis desk position (days).
# Positions must be exited or explicitly renewed at this boundary.

BASIS_DESK_BASIS_DRAWDOWN_HALT_RATIO = 0.5
# If cumulative basis loss exceeds 50% of cumulative funding income collected so far,
# exit immediately. Checked every 8 hours (after each funding settlement).

BASIS_DESK_MIN_FUNDING_PERSISTENCE = 0.6
# Minimum funding persistence to enter. Higher than extreme_funding because
# this is a multi-day position — requires more stable funding stream.

BASIS_DESK_MIN_MAKER_FILL_RATE = 0.70
# Minimum fraction of entries that must be filled as maker (not taker).
# Below this, the cost model breaks down and edge disappears.
# Monitored in shadow mode; if below threshold, strategy is halted.
