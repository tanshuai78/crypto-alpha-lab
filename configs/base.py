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
