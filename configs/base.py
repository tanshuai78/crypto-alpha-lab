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

EXTREME_FUNDING_WATCH_SYMBOLS = (
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BTC/USDT",
)
# Symbols monitored by Phase 1A watchlist mode, ordered by historical priority.

EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 30.0
# Observation-only threshold for premium-derived pre-signal alerts.

EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 50.0
# Stronger watchlist threshold requiring persistence and OI confirmation.

EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT = 100.0
# Historical trade-like threshold. Phase 1A must not produce executable trades from it.

EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN = 30
# Rolling micro window length for premium-derived observation persistence.

EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC = 300
# Minimum timestamp coverage before emitting a Phase 1A watch event.
# 300s = 5 minutes. Prevents startup false positives from 1-2 samples.

EXTREME_FUNDING_MICRO_PERSISTENCE_MIN = 0.70
# Strong micro persistence threshold.

EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK = 0.50
# Weak micro persistence threshold for watch_level_1.

EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT = 0.0
# Minimum 1h OI change for watch_level_2.

EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT = 3.0
# Minimum 1h OI change for watch_level_3.

EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC = 10
# Public mark/premium polling interval for observation daemon.

EXTREME_FUNDING_OI_POLL_INTERVAL_SEC = 60
# Open interest polling interval.

EXTREME_FUNDING_KLINE_REFRESH_INTERVAL_SEC = 3600
# Kline baseline refresh interval; do not fetch 720 candles every 10 seconds.

EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC = 300
# Heartbeat print interval for daemon status.

EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC = 30
# Maximum age for mark/premium data before classifying as stale.

EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC = 180
# Maximum age for OI data before classifying as stale.

EXTREME_FUNDING_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
# Binance USD-M futures public REST base URL used by Phase 1A observation daemon.

EXTREME_FUNDING_HTTP_TIMEOUT_SEC = 10.0
# Timeout for each public REST request. Keep conservative to avoid hanging the daemon.

EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS = 3
# Default bounded local dry-run loop count. Server mode may override to run forever.

EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC = 3600
# Lookback window for open-interest change confirmation.

EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC = 5.0
# Sleep duration after a recoverable polling-loop error.

EXTREME_FUNDING_EVENT_LOG_JSONL = "extreme_funding_watch_events.jsonl"
# File name for low-frequency JSONL evidence.

# Extreme Funding Phase 1B candidate builder. Observation-only thresholds.
EXTREME_FUNDING_MIN_NET_EDGE_BPS = 30.0
# Minimum net edge required after basis cost and estimated total cost.

EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO = 0.50
# Maximum allowed basis absorption ratio for candidate acceptance.

EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS = 1
# Conservative default holding intervals for candidate admission.

EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS = 50.0
# Minimum expected funding income in bps for Phase 1B admission.

EXTREME_FUNDING_FEE_BPS = 8.0
# Fee component in bps used by Phase 1B/1C cost decomposition.

EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS = 8.0
# Slippage reserve component in bps used by Phase 1B/1C cost decomposition.

EXTREME_FUNDING_ROLLBACK_RESERVE_BPS = 10.0
# Rollback reserve component in bps used by Phase 1B/1C cost decomposition.

EXTREME_FUNDING_MAX_SLIPPAGE_BPS = 10.0
# Maximum allowed slippage component in bps for Phase 1B candidate acceptance.

# Extreme Funding Phase 1C shadow simulator. No live execution.
EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS = 3
# Maximum intervals simulated by Phase 1C shadow simulator.

EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT = 15.0
# Exit condition when annualized funding decays below this level.

EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO = 0.50
# Exit condition when basis loss exceeds this fraction of cumulative funding income.

# Extreme Funding historical basis-aware replay.
EXTREME_FUNDING_BASIS_REPLAY_INTERVAL = "1m"
# Kline interval used for historical basis replay alignment.

EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS = 120_000
# Maximum absolute distance between funding settlement and selected price proxy.

EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS = 300_000
# Public kline request window around each funding settlement.

EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC = 20.0
# Public REST timeout for historical basis replay.

EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC = 0.2
# Sleep between replay REST requests to avoid aggressive polling.

EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER = 2.0
# Static depth proxy multiplier against RISK_MAX_SINGLE_POSITION_USDT.

EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR = "reports/extreme_funding"
# Output directory for historical basis-aware replay artifacts.


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
