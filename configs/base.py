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

EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT = 100.0
# Minimum annualized funding rate (%) to qualify as an anchor event (Layer A).
# This is a research gate, not a live trading trigger.

EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS = 15.0
# Minimum single-interval gross funding income (bps) for Layer B research shadow cases.
# Deliberately lower than Layer C trade gate to retain more historical tails for analysis.

EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO = 0.70
# Maximum basis absorption ratio for Layer B research shadow cases.
# Layer C keeps stricter trade gate via EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO.

EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS = 1
# Layer C trade candidate admission must pass under one funding interval assumption.

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

# Extreme Funding pre-orderbook parameter sensitivity audit.
EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT = (80.0, 100.0, 120.0)
# Annualized funding threshold sweep for candidate gating stress test.

EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS = (30.0, 50.0, 70.0)
# Expected funding income threshold sweep. 50 bps is current baseline.

EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS = (8.0, 10.0, 12.0)
# Max slippage threshold sweep to test cost tolerance sensitivity.

EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID = (1, 2)
# Holding-interval assumption sweep: 1 (conservative) and 2 (optimistic).

EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID = (0.30, 0.50, 0.70)
# Basis absorption threshold sweep to measure basis-cost gate sensitivity.


# ─── Strategy: Trend / Liquidation Regime ────────────────────────────────────

TREND_REGIME_WATCH_SYMBOLS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
)
# Phase 1A observation universe. Keep narrow for personal-capital directional risk.

TREND_REGIME_MAJOR_SYMBOLS = ("BTC/USDT", "ETH/USDT")
# Major symbols use lower movement/liquidation thresholds.

TREND_REGIME_LARGE_ALT_SYMBOLS = ("SOL/USDT", "XRP/USDT", "DOGE/USDT")
# Large alt symbols need stronger thresholds because 1h noise is higher.

TREND_REGIME_VOL_BREAKOUT_MULTIPLIER = 2.5
# Current 1h volatility must exceed N x 30-day baseline to qualify as a vol breakout.

TREND_REGIME_MAX_HOLDING_HOURS = 12
# Hard holding cap for directional shadow trades.

TREND_REGIME_STOP_LOSS_PCT = 1.5
# Per-trade hard stop loss percent.

TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR = 2.0
# Minimum absolute 1h return for BTC/ETH.

TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT = 2.5
# Minimum absolute 1h return for SOL/XRP/DOGE.

TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR = 1.5
# Minimum absolute 1h OI change for BTC/ETH.

TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT = 2.0
# Minimum absolute 1h OI change for SOL/XRP/DOGE.

TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR = 10_000_000.0
# Minimum 1h liquidation notional for BTC/ETH liquidation-cascade confirmation.

TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT = 3_000_000.0
# Minimum 1h liquidation notional for SOL/XRP/DOGE liquidation-cascade confirmation.

TREND_REGIME_MIN_24H_VOLUME_USDT = 300_000_000.0
# Minimum 24h volume for Phase 1A rows.

TREND_REGIME_MAX_DATA_AGE_SEC = 30
# Maximum accepted row age before stale rejection.

TREND_REGIME_OBSERVATION_COST_BPS = 30.0
# Base cost assumption (fees + slippage) for observation shadow validation.

TREND_REGIME_STRESS_COST_BPS = 50.0
# Stress cost assumption for liquidation and fast-breakout exits.

TREND_REGIME_MAX_SLIPPAGE_BPS = 8.0
# Max estimated slippage allowed for observation candidate generation.

TREND_REGIME_EVENT_LOG_JSONL = "trend_regime_watch_events.jsonl"
# JSONL artifact path for observation daemon events.

TREND_REGIME_FORCE_ORDER_RAW_JSONL = "trend_regime_force_orders_raw.jsonl"
# Raw Binance forceOrder events collected locally for replayable liquidation proxy history.

TREND_REGIME_FORCE_ORDER_RAW_ROTATE_MAX_BYTES = 512 * 1024 * 1024
# Auto-rotate the active raw archive once it reaches this size to prevent unbounded growth.

TREND_REGIME_FORCE_ORDER_RAW_ROTATE_BACKUP_DIR = "data/backup"
# Backup directory used when rotating the active raw archive.

TREND_REGIME_LIQUIDATION_HOURLY_JSONL = "trend_regime_liquidation_hourly.jsonl"
# Hourly symbol-level liquidation proxy derived from local forceOrder raw events.

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


# ─── Strategy: Liquidation-Only 5m Research ───────────────────────────────

LIQUIDATION_ONLY_5M_MAJOR_ABS_THRESHOLD_USDT = 50_000.0
# Minimum absolute liquidation notional for majors (BTC/ETH).
# Excludes smaller signals that act as transient noise.

LIQUIDATION_ONLY_5M_ALT_ABS_THRESHOLD_USDT = 10_000.0
# Minimum absolute liquidation notional for large alts (SOL/XRP/DOGE).
# Set lower due to smaller book size and lower average event notional.

LIQUIDATION_ONLY_5M_RELATIVE_SCORE_THRESHOLD = 0.99
# Percentile threshold against the rolling distribution.
# 0.99 = Top 1% of liquidation events in the lookback window.

LIQUIDATION_ONLY_5M_ROLLING_LOOKBACK_DAYS = 7
# Rolling lookback window length in days for the baseline distribution.
# 7 days of 5m intervals = 2016 bars.

LIQUIDATION_ONLY_5M_FORWARD_HORIZONS_BARS = (1, 2, 3)
# Holding periods to analyze after the event trigger (in 5m bars).

LIQUIDATION_ONLY_5M_DOMINANCE_RATIO_MIN = 0.70
# Minimum dominance ratio of the dominant liquidation direction.
# Dominance = max(long_liq, short_liq) / (long_liq + short_liq).
# Prevents taking signals in heavily mixed two-sided liquidation bars.

LIQUIDATION_ONLY_5M_ASSUMED_MIN_ROUND_TRIP_COST_BPS = 16.0
# Assumed minimum execution friction in bps (taker entries, commissions, slippage).
# Used to adjust gross forward returns for viability screening.


# ─── Strategy: Liquidation Shock 1m Event Study ──────────────────────────────

LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT = 50_000.0
# Minimum absolute liquidation notional for majors (BTC/ETH).
# Excludes smaller signals that act as transient noise.

LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT = 10_000.0
# Minimum absolute liquidation notional for large alts (SOL/XRP/DOGE).
# Set lower due to smaller book size and lower average event notional.

LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD = 0.99
# Percentile threshold against the rolling distribution.
# 0.99 = Top 1% of liquidation events in the lookback window.

LIQUIDATION_SHOCK_1M_LOOKBACK_HOURS = 24
# Trailing window size in hours for relative percentile shock scoring.

LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS = 1440
# Minimum number of 1m bars required in lookback window to calculate scores.

LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN = 0.70
# Minimum dominance ratio of the dominant liquidation direction.
# Dominance = max(long_liq, short_liq) / (long_liq + short_liq).

LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES = 5
# Deduplication window size in minutes to group events.

LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES = (5, 10, 15)
# Response observation horizons in minutes (evaluated exits at M+5, M+10, M+15).

LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS = 10.0
# Minimum return in bps to classify price response as directional (up or down).

LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO = 0.80
# Minimum required coverage ratio of data span for feasibility check.

LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES = 180
# Maximum allowed gap between returned liquidation event minutes.

LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS = 24.0
# Minimum evaluation hours required after lookback window.

LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS = 10
# Minimum total events across all symbols to qualify the event study.

LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H = 1.0
# Minimum normalized average events per 24 hours.

LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT = 2
# Minimum number of symbols that must have at least LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS.

LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.70
# Maximum fraction of total events contributed by a single symbol.

LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS = 0.55
# Minimum directional ratio (e.g. 55%) to indicate non-random edge.

LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS = 0.55
# Minimum directional ratio under the minimum move filter.

LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT = 2
# Minimum number of adjacent horizons passing directional bias checks.

LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS = 2
# Minimum number of events required for a single symbol to be included.

LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS = 2.0
# Minimum absolute median return in bps to be economically non-trivial.


# ─── Binance Liquidation Snapshot Event Study ──────────────────────────────────
# All constants for the Phase 1 Binance Vision historical snapshot research.
# Data semantics: liquidationSnapshot = largest-order snapshot proxy per symbol
# per 1000ms interval. NOT a complete liquidation tape.
# Sample window: 2024-01 to 2024-03 (Q1 2024 trending crypto market).
# Generalization of results to other windows is explicitly disallowed.

BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
)
# Futures perpetual symbols to study. USDT-margined Binance Futures.

BINANCE_LIQUIDATION_SNAPSHOT_MONTHS = ("2024-01", "2024-02", "2024-03")
# Calendar months to download and study. YYYY-MM format.

BINANCE_LIQUIDATION_SNAPSHOT_RAW_DIR = "data/binance_liquidation_snapshot/raw"
# Root directory for downloaded raw ZIP files (klines + liquidationSnapshot).
# Do not commit ZIP files.

BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR = "data/binance_liquidation_snapshot/extracted"
# Root directory for extracted CSV files.
# Do not commit extracted CSVs.

BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR = "data/binance_liquidation_snapshot/processed"
# Directory for the final processed JSONL event-study dataset.
# Do not commit processed JSONL.

BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO = 0.99
# Minimum required price data coverage ratio per symbol-month.
# 0.99 = at most 1% of 1m bars may be missing from the expected minute grid.

BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES = 1
# Maximum allowed consecutive missing 1m price bars.
# Any gap > 1m in the kline series causes that symbol-month to fail the price gate.

BINANCE_LIQUIDATION_SNAPSHOT_MIN_TOTAL_EVENTS = 10
# Minimum total shock events across all symbols to qualify the event density gate.

BINANCE_LIQUIDATION_SNAPSHOT_MIN_EVENTS_PER_MONTH = 1
# Minimum shock events per calendar month to qualify the event density gate.
# Set low for Phase 1 to avoid false rejection of sparse snapshot data.


# ─── Strategy Research: Route C1 Post-Liquidation Price Risk ─────────────────

ROUTE_C1_EVENT_PERCENTILE_THRESHOLD = 0.995
# Event percentile threshold forSame-Symbol Same-Side 1m liquidations.

ROUTE_C1_REQUIRED_REFERENCE_BARS = 1440
# Reference window bars (24 hours of 1m bars).

ROUTE_C1_DOMINANCE_RATIO_MIN = 0.65
# Minimum dominance ratio to select direction.

ROUTE_C1_DEDUP_BUCKET_MINUTES = 5
# Deduplication window size in minutes.

ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT = 50_000.0
# Major symbol (BTC/ETH) absolute liquidation threshold.

ROUTE_C1_ALT_ABS_THRESHOLD_USDT = 10_000.0
# Alt symbol (SOL/XRP/DOGE) absolute liquidation threshold.

ROUTE_C1_BASELINE_MATCH_COUNT = 20
# Matched control baseline sample size (K=20).

ROUTE_C1_BASELINE_MATCH_RATE_MIN = 0.70
# Minimum baseline match rate (70%).

ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX = 1.2
# Weak post-event volatility ratio threshold.

ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX = 1.2
# Weak post-event high-low range ratio threshold.

ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX = 1.1
# Weak post-event absolute excursion ratio threshold.


# ─── Strategy: Cross-Sectional Factor Lab Stage 0 ────────────────────────────

FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED = 540
# Number of historical days required for daily OHLCV coverage audit.

FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY = 30
# Minimum number of symbols passing static exclusion and liquidity threshold to proceed.

FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN = 0.95
# Minimum required daily OHLCV coverage ratio (valid daily count / expected daily count).

FACTOR_LAB_STAGE0_FUNDING_COVERAGE_MIN = 0.90
# Minimum required funding rate history coverage ratio for swappable perps.

FACTOR_LAB_STAGE0_OPEN_INTEREST_RECENT_DAYS_REQUIRED = 30
# Number of recent days required for checking open interest data readiness.

FACTOR_LAB_STAGE0_OPEN_INTEREST_RECENT_COVERAGE_MIN = 0.90
# Minimum required open interest coverage ratio over the recent days window.

FACTOR_LAB_STAGE0_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT = 20_000_000.0
# Minimum 30-day median daily quote volume in USDT for static liquidity screening.

FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS = True
# Whether to statically exclude wrapped/synthetic tokens (e.g. WBTC, WETH) from the universe.


# ─── Strategy: Cross-Sectional Factor Lab Stage A v1 ─────────────────────────

FACTOR_LAB_STAGEA_HISTORY_DAYS = 540
# Number of complete UTC daily bars used by Stage A v1.

FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS = 30
# Momentum lookback excluding the skipped recent day.

FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS = 1
# Number of most recent complete daily bars skipped before signal calculation.

FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC = 0
# Monday in Python weekday convention. Rebalance is Monday 00:00 UTC.

FACTOR_LAB_STAGEA_PRIMARY_TOP_N = 10
# Primary long-only equal-weight portfolio size.

FACTOR_LAB_STAGEA_DIAGNOSTIC_TOP_N = 5
# Diagnostic-only concentrated portfolio size. Not used for primary pass/fail.

FACTOR_LAB_STAGEA_COST_SCENARIOS_ROUND_TRIP_BPS = (30.0, 50.0, 80.0)
# Base/stress/crash round-trip cost scenarios for weekly spot rotation.

FACTOR_LAB_STAGEA_OPTIMISTIC_DIAGNOSTIC_PER_LEG_BPS = 10.0
# Optimistic maker-like per-leg cost, diagnostic only and not part of primary decision.

FACTOR_LAB_STAGEA_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT = FACTOR_LAB_STAGE0_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT
# Point-in-time rolling 30d median quote volume gate for Stage A.

FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT = 50
# Minimum effective weekly rebalance count for a valid 540d backtest.

FACTOR_LAB_STAGEA_MAX_DRAWDOWN_VS_EW_MULTIPLIER = 1.25
# Strategy max drawdown must not exceed equal-weight drawdown by more than this multiplier.

FACTOR_LAB_STAGEA_MAX_SINGLE_SYMBOL_PNL_CONTRIBUTION_SHARE = 0.35
# Maximum allowed share of total PnL contribution from one symbol.

FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE = 0.30
# Maximum allowed share of total PnL contribution from one calendar month.

FACTOR_LAB_STAGEA_MAX_INSUFFICIENT_UNIVERSE_RATIO = 0.10
# Maximum allowed fraction of rebalance dates with fewer than top-N eligible symbols.


# ─── Strategy: Cross-Sectional Factor Lab Stage A2 ─────────────────────────

FACTOR_LAB_STAGEA2_BTC_MA_DAYS = 20
# BTC regime filter lookback. Uses BTC close from t-20 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS = 20
# Alt universe regime filter lookback. Uses t-21 through t-1.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO = 0.80
# Minimum share of eligible symbols with valid 20d returns for alt universe regime.

FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS = FACTOR_LAB_STAGEA_PRIMARY_TOP_N
# Minimum valid symbol count for alt universe regime decision.

FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT = 30.0
# Minimum max drawdown reduction versus regime_none baseline.

FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE = 0.60
# Mostly-cash filters cannot unlock Stage A2 Round 2.

FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT = 10.0
# Strategy may not underperform BTC or ETH by more than 10 percentage points under base 30 bps cost.

FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT = FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT
# Stage A2 inherits Stage A v1 minimum effective rebalance sample size.

FACTOR_LAB_STAGEA2_ALLOWED_VARIANTS = (
    "regime_none",
    "btc_ma20_cash",
    "alt_universe_20d_return_cash",
)
# Only these Stage A2 Round 1 variants are allowed.


# Stage A2.2 CMOM diagnostic constants.
FACTOR_LAB_STAGEA2_CMOM_LOOKBACK_DAYS = 14
FACTOR_LAB_STAGEA2_CMOM_SKIP_RECENT_DAYS = 1
FACTOR_LAB_STAGEA2_CMOM_MIN_RETURN_DIFF_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_MAX_BTC_UNDERPERFORMANCE_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_MAX_ETH_UNDERPERFORMANCE_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_MIN_REBALANCE_COUNT = FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT
FACTOR_LAB_STAGEA2_CMOM_MIN_EW_IMPROVEMENT_DIFF_PCT = 5.0
FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_DRAWDOWN_WORSENING_PCT = 5.0
FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_TOP5_UNDERPERFORMANCE_PCT = 10.0
FACTOR_LAB_STAGEA2_CMOM_MAX_3D_DIAGNOSTIC_MONTH_SHARE = 0.50
FACTOR_LAB_STAGEA2_CMOM_MIN_PROCEED_TOTAL_RETURN_PCT = -50.0
FACTOR_LAB_STAGEA2_CMOM_MIN_PROCEED_STRESS_50BPS_RETURN_PCT = -60.0
FACTOR_LAB_STAGEA2_CMOM_LIVE_SAFE = False
FACTOR_LAB_STAGEA2_CMOM_PAPER_SHADOW_ALLOWED = False
FACTOR_LAB_STAGEA2_CMOM_VARIANTS = (
    "momentum_30d_skip_1d",
    "cmom_14d_skip_1d",
)


# ─── Research: External Signal Shadow Lab Stage 0 ─────────────────────────────

EXTERNAL_SIGNAL_SHADOW_MIN_LIQUIDITY_USD = 500_000.0
# Minimum token liquidity for accepting an external event into shadow replay.

EXTERNAL_SIGNAL_SHADOW_MAX_SELL_TAX_PCT = 5.0
# Maximum allowed sell tax for token events; higher values are rejected.

EXTERNAL_SIGNAL_SHADOW_MAX_TOP10_HOLDER_SHARE = 0.35
# Maximum top-10 holder concentration. 0.35 = 35%.

EXTERNAL_SIGNAL_SHADOW_MAX_SMART_MONEY_EXIT_RATE = 0.70
# Maximum allowed smart-money exit rate. 0.70 = 70%.

EXTERNAL_SIGNAL_SHADOW_CEX_MAX_SPREAD_BPS = 10.0
# CEX event rejection threshold for current spread.

EXTERNAL_SIGNAL_SHADOW_CEX_MIN_DEPTH_10BPS_USD = 100_000.0
# Minimum CEX depth within 10 bps needed for shadow eligibility.

EXTERNAL_SIGNAL_SHADOW_MIN_ORDERBOOK_COVERAGE = 0.95
# Minimum recent orderbook coverage required for CEX events.

EXTERNAL_SIGNAL_SHADOW_MIN_PRICE_COVERAGE = 0.99
# Minimum price bar coverage required for any shadow replay.

EXTERNAL_SIGNAL_SHADOW_CUSUM_FIXED_THRESHOLD_BPS = 30.0
# Fixed lower bound for CUSUM confirmation threshold.

EXTERNAL_SIGNAL_SHADOW_CUSUM_VOL_MULTIPLIER = 1.5
# Rolling-volatility multiplier used by CUSUM threshold.

EXTERNAL_SIGNAL_SHADOW_CUSUM_CONFIRMATION_WINDOW_MIN = 30
# Maximum minutes after event time to wait for CUSUM confirmation.

EXTERNAL_SIGNAL_SHADOW_TAKE_PROFIT_BPS = 150.0
# Default triple-barrier take-profit distance.

EXTERNAL_SIGNAL_SHADOW_STOP_LOSS_BPS = 100.0
# Default triple-barrier stop-loss distance.

EXTERNAL_SIGNAL_SHADOW_MAX_HOLDING_MINUTES = 240
# Default vertical barrier horizon.

EXTERNAL_SIGNAL_SHADOW_ENTRY_DELAY_BARS = 1
# Number of complete bars after trigger before shadow entry.

EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS = 50.0
# Default round-trip cost used for shadow net return.

# ─── Research: External Signal Shadow Lab Stage 1 Connector ──────────────────

EXTERNAL_SIGNAL_CONNECTOR_EVENT_TIME_BUCKET_MS = 5 * 60 * 1000
# Semantic dedup bucket width. Prevents repeated website/API refreshes from inflating event density.

EXTERNAL_SIGNAL_CONNECTOR_MAX_CEX_LATENCY_MS = 15 * 60 * 1000
# Maximum allowed latency for CEX / market rank payloads.

EXTERNAL_SIGNAL_CONNECTOR_MAX_ONCHAIN_LATENCY_MS = 60 * 60 * 1000
# Maximum allowed latency for on-chain / audit / holder payloads.

EXTERNAL_SIGNAL_CONNECTOR_MAX_MANUAL_FIXTURE_LATENCY_MS = 24 * 60 * 60 * 1000
# Maximum allowed latency for manual fixture payloads. Not alpha-valid.

EXTERNAL_SIGNAL_CONNECTOR_VERSION = "stage1_v0"
# Connector version written into normalized event metadata and summaries.

EXTERNAL_SIGNAL_CONNECTOR_SCHEMA_VERSION = "external_signal_event_v1"


EXTERNAL_SIGNAL_STAGE1_1_SOURCE = "gate_marketanalysis_manual_export"
# Internal source id for Stage 1.1 manual-export dry run. Not a vendor API name.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_VENDOR = "gate"
# External vendor label used for source attribution in summaries and reviews.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SURFACE = "gate_big_data_dashboard"
# Human-readable surface where manual observations are collected.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_CAPTURE_METHOD = "manual_export"
# Capture method for Stage 1.1. HTTP/API collection remains explicitly out of scope.

EXTERNAL_SIGNAL_STAGE1_1_SOURCE_SKILL = "gate_exchange_marketanalysis"
# Internal source_skill label used when normalizing manually captured market-analysis payloads.

EXTERNAL_SIGNAL_STAGE1_1_ALLOWED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
# CEX majors whitelist for Stage 1.1. Prevents a manual Gate dashboard dry run from drifting into small-cap discovery.

EXTERNAL_SIGNAL_STAGE1_1_MIN_RAW_PAYLOADS = 10
# Minimum raw manual-export payload count for connector-valid status. Below this, data density is insufficient even for dry run.

EXTERNAL_SIGNAL_STAGE1_1_MIN_EMITTED_EVENTS = 1
# Minimum normalized event count for connector-valid status. This is not enough for Stage 0 handoff.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_RAW_PAYLOADS = 20
# Minimum raw manual-export payload count before Stage 0 handoff can be considered. Safe range: 20-100 for manual dry run.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_EMITTED_EVENTS = 5
# Minimum emitted event count before Stage 0 handoff can be considered.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_SYMBOLS = 3
# Minimum distinct emitted symbols for handoff. Prevents single-symbol dashboard refreshes from looking like broad signal coverage.

EXTERNAL_SIGNAL_STAGE1_1_HANDOFF_MIN_UNIQUE_TIME_BUCKETS = 3
# Minimum distinct event-time buckets for handoff. Prevents one-time clustered samples from passing as source coverage.

EXTERNAL_SIGNAL_STAGE1_1_MAX_EVENT_TIME_FALLBACK_RATIO = 0.50
# Maximum fraction of emitted events whose event_time_ms was derived from available_at_ms. Above this, event timing is not replay-trustworthy.

EXTERNAL_SIGNAL_STAGE1_1_MAX_PRICE_MAPPING_UNAVAILABLE_RATIO = 0.30
# Maximum fraction of raw payloads quarantined because no local price series exists. Above this, source does not fit current lab coverage.

EXTERNAL_SIGNAL_STAGE1_1_MAX_REJECTED_PAYLOAD_RATIO = 0.30
# Maximum rejected/raw ratio for handoff readiness. High rejection means schema/source quality is unstable.

EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_SYMBOL_DOMINANCE_RATIO = 0.70
# Maximum emitted-event concentration in one symbol before source quality is considered too concentrated.

EXTERNAL_SIGNAL_STAGE1_1_MAX_SINGLE_TIME_BUCKET_DOMINANCE_RATIO = 0.70
# Maximum emitted-event concentration in one time bucket before source quality is considered too clustered.

EXTERNAL_SIGNAL_STAGE1_1_MAX_DUPLICATE_RATIO = 0.50
# Maximum deduped/raw ratio before source quality is considered dominated by repeated dashboard refreshes.

EXTERNAL_SIGNAL_STAGE1_1_MAX_UNKNOWN_EVENT_TYPE_RATIO = 0.30
# Maximum unsupported-event/raw ratio before source event taxonomy is considered too unstable.

EXTERNAL_SIGNAL_STAGE1_1_MAX_MISSING_REQUIRED_FIELD_RATIO = 0.30
# Maximum missing-required-field/raw ratio before manual payload quality is considered insufficient.

# Stage 1.2 Gate public REST base URL. Public-readonly only; no authenticated endpoints.
EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL = "https://api.gateio.ws/api/v4"

# Stage 1.2 Gate spot ticker path. Safe path must remain public market data.
EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH = "/spot/tickers"

# Stage 1.2 allowed Gate pairs. Keep small CEX majors only for first collector dry run.
EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS = (
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "XRP_USDT",
    "DOGE_USDT",
)

# Stage 1.2 HTTP timeout for public readonly calls. Safe range: 5-30 seconds.
EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC = 10.0

# Stage 1.2 retry count for public readonly calls. Safe range: 0-2; avoid API hammering.
EXTERNAL_SIGNAL_STAGE1_2_MAX_RETRIES = 1

# Stage 1.2 backoff between retry attempts. Safe range: 1-10 seconds.
EXTERNAL_SIGNAL_STAGE1_2_RETRY_BACKOFF_SEC = 2.0

# Stage 1.2 delay between per-symbol public calls. Safe range: 0.1-2.0 seconds; reduces 429 risk.
EXTERNAL_SIGNAL_STAGE1_2_INTER_REQUEST_DELAY_SEC = 0.3

# Stage 1.2 User-Agent. Identifies research-only readonly collector; not a trading client.
EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT = "crypto-alpha-lab-research-readonly/0.1"

# ExternalSignalEvent-compatible output schema version.

# ─── External Signal Shadow Lab Stage 1.3 Candidate Discovery ────────────────

EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD = 3.0
# Candidate A volume spike threshold. 3.0 means current 1h quote volume must be
# at least 3x the rolling same-hour median. Research-only; do not tune after results.

EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD = 1.5
# Candidate B relative-strength threshold in rolling std units. Safe range for
# pre-registered diagnostics: 1.0-2.5. Do not grid-search in Stage 1.3.

EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS = 7
# Rolling historical window length for volume and return baselines.

EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES = 5
# Minimum same-hour historical samples required before volume_spike_1h can emit.

EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES = 48
# Minimum 1h relative-strength samples required before z-threshold evaluation.

EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES = 15
# Historical snapshot interval. Matches Stage 1.3 replay granularity, not live cadence.

EXTERNAL_SIGNAL_STAGE1_3_ONE_HOUR_BAR_COUNT = 4
# Number of 15m bars used to construct a complete 1h observation window.

EXTERNAL_SIGNAL_STAGE1_3_FORWARD_4H_BAR_COUNT = 16
# Number of 15m bars used for the fixed 4h primary forward-return window.
# Keep centralized so replay, metrics, and eligibility checks cannot drift.

EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_PREFERRED = 180
# Preferred historical replay span. Longer improves event diversity.

EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN = 90
# Minimum historical replay span before Stage 1.3 can run without data warning.

EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS = 60_000
# Synthetic availability lag added to historical bar close time to prevent same-bar fills.

EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS = 1
# Minimum complete 15m bars to wait after candidate event before evaluating entry.

EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_COUNT = 100
# Minimum candidate event count for data sufficiency.

EXTERNAL_SIGNAL_STAGE1_3_MIN_EVENT_DAYS = 20
# Minimum distinct event days for data sufficiency.

EXTERNAL_SIGNAL_STAGE1_3_MIN_SYMBOLS_WITH_EVENTS = 3
# Minimum distinct symbols with candidate events.

EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.50
# Max share of events from one symbol. Prevents single-symbol overfit.

EXTERNAL_SIGNAL_STAGE1_3_MAX_SINGLE_DAY_EVENT_SHARE = 0.20
# Max share of events from one UTC day. Prevents one-day regime overfit.

EXTERNAL_SIGNAL_STAGE1_3_MAX_TOP5_POSITIVE_PNL_SHARE = 0.30
# Max gross profit contribution from top 5 positive events.

EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS = 500
# Number of random baseline trials. Fixed for comparability.

EXTERNAL_SIGNAL_STAGE1_3_RANDOM_SEED = 20260613
# Fixed seed for reproducible random baseline generation.

EXTERNAL_SIGNAL_STAGE1_3_COST_SCENARIOS_ROUND_TRIP_BPS = (30.0, 50.0, 80.0)
# Round-trip cost scenarios: base, stress, crash. Research-only, not fee advice.

EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO = 0.98
# Minimum 15m bar coverage per symbol before replay can be trusted.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_BASE_URL = "https://data-api.binance.vision"
# Public market-data-only Binance base URL used for Stage 1.3 historical proxy replay.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_KLINES_PATH = "/api/v3/klines"
# Public spot kline endpoint path. Must remain readonly and unauthenticated.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
# Required major-symbol universe for Stage 1.3 Binance proxy replay.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_INTERVAL = "15m"
# Historical kline interval required by Stage 1.3 replay.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_KLINES_LIMIT = 1000
# Max spot kline rows per request. Binance spot endpoint maximum is 1000.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_TIMEOUT_SEC = 10.0
# Public HTTP timeout for Binance proxy kline requests. Safe range: 5-30 seconds.

EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_REQUEST_SLEEP_SEC = 0.2
# Delay between public kline requests. Keeps the one-off replay builder polite.


# ─── External Signal Shadow Lab Stage 1.4A Derivatives Stress Data Feasibility ─

EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
# Mapped symbol universe for USD-M futures.

EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_PREFERRED = 180
# Preferred historical days for full composite replay.

EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN = 90
# Minimum historical days for a source to be considered usable.

EXTERNAL_SIGNAL_STAGE1_4_MIN_USABLE_SYMBOLS = 3
# Minimum number of symbols that must pass all feasibility thresholds.

EXTERNAL_SIGNAL_STAGE1_4_BAR_COVERAGE_MIN_RATIO = 0.95
# Minimum bar coverage ratio for price history data.

EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO = 0.90
# Minimum coverage of non-null fields in liquidation records.

EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO = 0.90
# Minimum time continuity coverage for liquidation data.

EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO = 0.95
# Minimum coverage of non-null fields in funding rate records.

EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO = 0.95
# Minimum ratio of expected 8h funding settlements actually found.

EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO = 0.90
# Minimum coverage of non-null fields in open interest records.

EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO = 0.90
# Minimum time continuity coverage for open interest records.

EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_FUNDING_INTERVAL_MS = 8 * 60 * 60 * 1000
# Expected 8h cadence for funding settlements (in milliseconds).

EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_OI_INTERVAL_MS = 60 * 60 * 1000
# Expected 1h cadence for open interest data (in milliseconds).

EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_PRICE_INTERVAL_MS = 15 * 60 * 1000
# Expected 15m price bar interval (in milliseconds).

EXTERNAL_SIGNAL_STAGE1_4_FUNDING_PUBLISH_LAG_MS = 15 * 60 * 1000
# Delay after settlement time before funding rate becomes available/published.

EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_WINDOWS = 50
# Minimum composite overlap windows (candidate event entries) for preview density.

EXTERNAL_SIGNAL_STAGE1_4_PREVIEW_MIN_COMPOSITE_OVERLAP_DAYS = 15
# Minimum distinct days covered by composite overlap windows.

EXTERNAL_SIGNAL_STAGE1_4_BINANCE_FAPI_BASE_URL = "https://fapi.binance.com"
# Base URL for Binance USD-M Futures public REST API.

EXTERNAL_SIGNAL_STAGE1_4_FUNDING_RATE_PATH = "/fapi/v1/fundingRate"
# Public endpoint path for funding rate history.

EXTERNAL_SIGNAL_STAGE1_4_OPEN_INTEREST_HIST_PATH = "/futures/data/openInterestHist"
# Public endpoint path for open interest history.

EXTERNAL_SIGNAL_STAGE1_4_CURRENT_OPEN_INTEREST_PATH = "/fapi/v1/openInterest"
# Public endpoint path for current open interest.

EXTERNAL_SIGNAL_STAGE1_4_FUTURES_KLINES_PATH = "/fapi/v1/klines"
# Public endpoint path for futures kline historical bars.

EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_BASE_URL = "https://data.binance.vision"
# Base URL for Binance Vision public data archives.

EXTERNAL_SIGNAL_STAGE1_4_TIMEOUT_SEC = 10.0
# Request timeout in seconds for public readonly queries.

EXTERNAL_SIGNAL_STAGE1_4_REQUEST_SLEEP_SEC = 0.2
# Polite delay between public requests to avoid hitting rate limits.

EXTERNAL_SIGNAL_STAGE1_4_LOCAL_OI_ARCHIVE_GLOB = "data/external_signal_shadow/derivatives_stress/oi/*.jsonl"
# Glob path for scanning local Open Interest archive files.

EXTERNAL_SIGNAL_STAGE1_4_LOCAL_FORCE_ORDER_ARCHIVE_GLOB = "data/trend_regime_force_orders_raw.jsonl"
# File path/glob for scanning local force order (liquidation) archives.

EXTERNAL_SIGNAL_STAGE1_4_CM_TO_UM_SYMBOL_MAP = {
    "BTCUSD_PERP": "BTCUSDT",
    "ETHUSD_PERP": "ETHUSDT",
    "SOLUSD_PERP": "SOLUSDT",
    "XRPUSD_PERP": "XRPUSDT",
    "DOGEUSD_PERP": "DOGEUSDT",
}
# Mapping from Coin-M symbols to USD-M symbols for liquidation snapshots proxying.


# Binance Vision daily metrics ZIP path template for USD-M futures OI archive.
# This is the public historical source for sum_open_interest and sum_open_interest_value.
EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_METRICS_DAILY_PATH_TEMPLATE = (
    "/data/futures/um/daily/metrics/{symbol}/{symbol}-metrics-{date}.zip"
)

# Local JSONL output path for converted Binance Vision metrics OI rows.
# Runtime data should remain ignored by git unless explicitly reviewed.
EXTERNAL_SIGNAL_STAGE1_4_BINANCE_VISION_OI_OUTPUT_JSONL = (
    "data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl"
)

# Public REST page limit used by Stage 1.4A funding/price historical probes.
# Safe range: 500-1500; do not exceed Binance endpoint limits.
EXTERNAL_SIGNAL_STAGE1_4_PUBLIC_REST_PAGE_LIMIT = 1000

# Preferred Stage 1.4A real audit history window.
# Must be >= EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN.
EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS = 180


# ─── External Signal Shadow Lab Stage 1.4A.2: Vendor Liquidation Audit ───

EXTERNAL_SIGNAL_STAGE1_4A2_VENDOR_ORDER = (
    "tardis_dev",
    "coinglass",
    "laevitas",
    "coinalyze",
    "coin_metrics_pro",
)
# Fixed first-pass vendor audit order. Do not expand the vendor list before this
# five-vendor audit is completed; otherwise the feasibility audit becomes open-ended.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_HISTORY_DAYS = 90.0
# Minimum verified liquidation sample history before a vendor can be considered feasible.
# Safe range: 90-180 days. Below 90d is insufficient for Stage 1.4B replay eligibility.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_SYMBOLS_WITH_USABLE_DATA = 3
# Minimum number of target symbols with usable sample rows.
# Safe range: 3-5. Fewer than 3 symbols makes source feasibility too concentrated.

EXTERNAL_SIGNAL_STAGE1_4A2_MAX_TIMESTAMP_RESOLUTION_MS = 60_000
# Coarsest timestamp resolution allowed for intraday Stage 1.4B replay candidates.
# 60s is acceptable for 15m/1h liquidation clusters; daily-only data is not.

EXTERNAL_SIGNAL_STAGE1_4A2_MIN_VENDOR_DATA_LAG_MS = 60_000
# Conservative minimum data availability lag when vendor samples do not provide true arrival time.
# Prevents replay anchoring on unavailable bucket-start timestamps.

EXTERNAL_SIGNAL_STAGE1_4A2_LOW_COST_MAX_USD_PER_MONTH = 50.0
# Maximum monthly cost considered low for personal research sample access.
# Above this, user cost approval is required before feasible can be claimed.

EXTERNAL_SIGNAL_STAGE1_4A2_MEDIUM_COST_MAX_USD_PER_MONTH = 200.0
# Maximum monthly cost considered medium. Costs above this or enterprise quote-only plans
# are degraded by default unless the user explicitly approves.


# ─── External Signal Shadow Lab Stage 1.4A-LQ30: Local ForceOrder Snapshot Diagnostic ───

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_HISTORY_DAYS = 15
# Minimum local forceOrder history span for LQ30 diagnostic to be meaningful.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_SYMBOLS_WITH_EVENTS = 3
# Minimum number of symbols with liquidation events.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_EVENT_DAYS = 10
# Minimum number of distinct days containing liquidation events.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ALIGNMENT_OVERLAP_EVENT_DAYS = 10
# Minimum days where liquidation windows align with funding/OI/price datasets.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.60
# Max allowed share of event count contributed by one symbol.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_DAY_EVENT_SHARE = 0.35
# Max allowed share of event count contributed by one day.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_DAY_NOTIONAL_SHARE = 0.50
# Max allowed notional concentration in the single largest day.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP3_DAYS_NOTIONAL_SHARE = 0.70
# Max allowed cumulative notional concentration in the top 3 days.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_SYMBOL_NOTIONAL_SHARE = 0.70
# Max allowed notional concentration in the single largest symbol.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO = 0.001
# Max acceptable invalid JSON line ratio if invalid rows are quarantined.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_15M_MS = 15 * 60 * 1000
# Fixed UTC 15m aggregation bucket.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_1H_MS = 60 * 60 * 1000
# Fixed UTC 1h aggregation bucket.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_CONFIGURED_LAG_MS = 60_000
# Conservative data lag applied after bucket_end when producing available_at_ms.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_FUNDING_PUBLISH_LAG_MS = 5 * 60 * 1000
# Expected delay for funding rate publication.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_OI_STALENESS_MS = 60 * 60 * 1000
# Maximum age allowed for OI data compared to bucket end to be considered aligned.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_FUNDING_RATE_PREVIEW = 0.0
# Minimum absolute funding rate to check preview condition.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_OI_CHANGE_RATIO_PREVIEW = 0.0
# Minimum absolute OI change ratio to check preview condition.

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_PRICE_RETURN_1H_PREVIEW = 0.0
# Minimum absolute price return 1h to check preview condition.

