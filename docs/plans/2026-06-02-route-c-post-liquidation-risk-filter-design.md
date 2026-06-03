# Route C: Post-Liquidation Risk Filter Research Design

**Date:** 2026-06-02

## 1. Core Positioning

Route C is not a direct continuation of the failed directional liquidation strategy.

The previous research asked a narrow directional question:

> After a 1m liquidation shock, can we predict the next 5/10/15m price direction?

That question was not confirmed by the available data. The failure came from both data-source limits and weak directional response structure.

Route C changes the question:

> After liquidation pressure appears, does the market become more dangerous to trade?

This is a lower-level and more practical question. It does not require predicting up or down. It only requires proving that post-liquidation windows have materially worse execution and risk conditions than normal matched windows.

If validated, Route C should first become a **risk filter / execution overlay**, not a standalone alpha strategy.

Potential live uses:

- pause new entries after liquidation shocks;
- reduce notional during unstable windows;
- widen slippage reserve;
- disable maker entry when the book is unstable;
- prohibit chase orders after forced moves;
- trigger temporary risk-off mode;
- add liquidation context to later regime or alpha models.

This makes Route C compatible with the existing system's capital-preservation design: it can improve trade quality without adding new directional exposure.

---

## 2. Why Route C Exists After Route A/B Failed

### 2.1 What Failed Before

The original liquidation strategy line tried to validate:

- 1m liquidation shock event;
- fixed 5/10/15m response;
- directional continuation or reversal;
- 5-symbol universe: BTC, ETH, SOL, XRP, DOGE.

Key failures:

- Coinalyze route lacked reliable 1m continuity.
- Binance Vision snapshot route was not a complete liquidation tape.
- Binance snapshot route failed full 5-symbol integrity.
- Reduced proxy sample did not confirm directional structure.
- Route A complete-quarter screening did not find a clean BTC/ETH/SOL quarter across 2023-Q1 to 2024-Q1.

The correct conclusion is not:

> Liquidation data is useless.

The better conclusion is:

> Liquidation data has not proven itself as a simple fixed-horizon directional alpha.

Route C is the disciplined response to that result.

### 2.2 Why Risk Filtering Is More Plausible Than Direction Prediction

Liquidation events are forced trades. They often coincide with:

- volatility expansion;
- fast price jumps;
- spread widening;
- temporary depth withdrawal;
- higher market-order impact;
- stop-loss cascades;
- maker adverse selection;
- unstable continuation/reversal behavior.

These effects can exist even when direction is not predictable.

In plain language:

- The market may not tell us where it will go.
- But it may tell us that this is a bad moment to enter normally.

That is exactly what Route C is designed to test.

---

## 3. Three Route C Stages

Route C has three stages. They are not three equal standalone strategies.

Recommended interpretation:

1. **C1 Post-Liquidation Volatility / Liquidity Filter**
   - risk module;
   - highest priority;
   - most directly useful for live trading.

2. **C2 Episode Pressure**
   - event-definition upgrade;
   - converts weak single-minute shocks into multi-minute pressure episodes.

3. **C3 Context-Conditioned Directionality**
   - alpha validation layer;
   - highest overfit risk;
   - should only run after C1/C2 produce stable event labels.

## 4. C1: Post-Liquidation Volatility / Liquidity Filter

### 4.1 Purpose

C1 asks:

> After a liquidation event, does volatility, adverse excursion, spread, depth, or impact cost become materially worse?

It does not ask:

> Can we predict price direction?

### 4.2 Why C1 Comes First

C1 is the most practical branch because it can improve the current trading system without creating a new alpha dependency.

If liquidation pressure reliably predicts worse execution conditions, the system can use it to block or downgrade risky trades.

This directly connects to current system constraints:

- slippage tolerance;
- impact cost filter;
- liquidity monitor;
- entry cooldown;
- risk-off controls;
- net exposure protection;
- orderbook-aware execution.

### 4.3 Event Definition

Initial event:

- symbol in BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT;
- 1m liquidation notional exceeds rolling threshold;
- threshold based on trailing 24h or 30d distribution;
- side retained as `long_liquidation` / `short_liquidation`;
- event timestamp aligned to 1m bucket.

Important: event direction is not used as a trade direction in C1.

### 4.4 Post-Event Metrics

Price-based metrics:

- `realized_vol_5m`;
- `realized_vol_10m`;
- `realized_vol_15m`;
- `realized_vol_30m`;
- `high_low_range_5m_bps`;
- `high_low_range_15m_bps`;
- `max_adverse_excursion_5m_bps`;
- `max_adverse_excursion_15m_bps`;
- `jump_return_abs_bps`;
- `stop_loss_overrun_proxy_bps`.

Orderbook-based metrics:

- `bid_ask_spread_bps`;
- `top1_depth_usdt`;
- `top5_depth_usdt`;
- `depth_within_5bps_usdt`;
- `depth_within_10bps_usdt`;
- `depth_within_20bps_usdt`;
- `orderbook_imbalance`;
- `estimated_impact_cost_500usdt_bps`;
- `estimated_impact_cost_1000usdt_bps`;
- `estimated_impact_cost_2000usdt_bps`;
- `maker_adverse_selection_proxy`.

Execution-risk decisions derived from these metrics:

- `pause_entry`;
- `reduce_notional`;
- `increase_slippage_reserve`;
- `disable_maker_first`;
- `force_taker_only_with_small_size`;
- `risk_off_cooldown`.

### 4.5 Baseline Comparison

C1 must not compare liquidation windows to all random minutes blindly.

Use matched baselines:

- same symbol;
- same exchange;
- same month;
- same time-of-day bucket where possible;
- similar pre-event 30m volatility percentile;
- no liquidation shock in baseline lookback window.

This avoids a false conclusion where liquidation events only look risky because they occur during already volatile sessions.

### 4.6 Continue / Stop Criteria

Continue C1 if:

- post-event realized volatility median >= matched baseline median * 1.5;
- post-event P75/P90 adverse excursion is materially higher than baseline;
- spread or impact cost deteriorates after the event;
- result holds for at least 2 of BTC/ETH/SOL;
- result does not collapse by month;
- orderbook deterioration appears within 1/5/10/15m after the event.

Stop or downgrade C1 if:

- post-event volatility is not materially different from matched baseline;
- only one symbol works;
- result only works in one month;
- orderbook metrics do not deteriorate;
- effect disappears after excluding already-high-volatility baseline windows.

### 4.7 Expected Output

Research output should be a risk-filter summary, not a PnL backtest first.

Required output fields:

```json
{
  "decision": "continue_route_c1|stop_route_c1|needs_more_forward_data",
  "data_window": "...",
  "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
  "event_count": 0,
  "matched_baseline_count": 0,
  "post_event_vol_ratio_median": 0.0,
  "post_event_mae_p90_bps": 0.0,
  "baseline_mae_p90_bps": 0.0,
  "spread_deterioration_ratio_median": 0.0,
  "impact_cost_deterioration_ratio_median": 0.0,
  "symbols_passing": [],
  "months_passing": [],
  "recommended_live_action": "observe_only|pause_entry|reduce_notional|risk_off"
}
```

---

## 5. C2: Episode Pressure

### 5.1 Purpose

C2 asks:

> Is a multi-minute liquidation pressure episode more informative than a single 1m shock?

Single-minute shocks can be noisy. A liquidation cascade is often a process, not one candle.

### 5.2 Why C2 Comes After C1

C2 adds complexity. It should only be built after C1 proves that liquidation pressure has risk-filter value.

If C1 fails, there is little reason to engineer more complex episodes.

If C1 succeeds, C2 can improve event quality:

- fewer isolated false positives;
- better pressure duration signal;
- better link to execution deterioration;
- better input for later directionality tests.

### 5.3 Episode Definition

Initial episode rule:

- rolling window: 3 to 10 minutes;
- at least N liquidation-positive minutes;
- same-side pressure ratio >= threshold;
- total liquidation notional above percentile threshold;
- allow short gaps of 1 minute;
- episode ends after pressure decays below threshold.

Candidate episode fields:

- `episode_start_ms`;
- `episode_end_ms`;
- `episode_duration_min`;
- `dominant_side`;
- `same_side_ratio`;
- `episode_total_notional_usdt`;
- `peak_1m_notional_usdt`;
- `pressure_decay_rate`;
- `price_displacement_during_episode_bps`;
- `post_episode_vol_15m`;
- `post_episode_mae_15m_bps`;
- `post_episode_spread_deterioration`.

### 5.4 What C2 Is For

C2 can serve two downstream purposes:

1. Improve C1 risk filters:
   - longer pressure episode may justify longer cooldown;
   - stronger same-side pressure may justify more aggressive notional reduction.

2. Prepare C3 direction tests:
   - direction tests should use episodes rather than isolated 1m shocks if episodes prove cleaner.

### 5.5 Continue / Stop Criteria

Continue C2 if:

- episodes reduce false positives versus 1m shocks;
- post-episode risk metrics are stronger than post-single-shock metrics;
- event density remains usable;
- at least 2 symbols produce sufficient episodes;
- by-month stability remains acceptable.

Stop C2 if:

- episode rules become too sparse;
- parameter choices are fragile;
- effect only appears after aggressive threshold tuning;
- episode labels do not improve C1 risk signal.

---

## 6. C3: Context-Conditioned Directionality

### 6.1 Purpose

C3 asks:

> Does liquidation pressure have directional value only under specific pre-locked market contexts?

This is the closest Route C gets to alpha.

It should not run first because it has high overfit risk.

### 6.2 Why C3 Is Risky

The previous directional branch failed under a simple fixed-horizon definition.

If we immediately start slicing by:

- trend;
- funding;
- OI;
- volatility;
- symbol;
- side;
- time of day;
- episode strength;

we may simply data-mine a small bucket that looks good by chance.

C3 must therefore use locked contexts and walk-forward evaluation.

### 6.3 Allowed Contexts

Only use contexts defined before running the analysis:

- previous 30m return direction;
- previous 30m realized volatility percentile;
- funding positive / negative / extreme;
- OI expanding / contracting;
- price above / below short moving average;
- orderbook imbalance regime;
- spread-normal / spread-wide regime.

Do not add new contexts after seeing results unless they are marked as exploratory and excluded from final confirmation.

### 6.4 C3 Output

C3 should output:

- directional ratio by context;
- PnL proxy after fees and slippage;
- event count by bucket;
- month split;
- symbol split;
- walk-forward stability;
- rejected contexts and why.

Promotion requires:

- enough events per bucket;
- stable out-of-sample behavior;
- net edge after estimated execution cost;
- no hidden net exposure increase;
- shadow-mode validation before live use.

---

## 7. Existing Data Assets

## 7.1 Live Liquidation Collector

Current server collector has started receiving real Binance forceOrder events.

This data remains useful and should continue running.

Minimum collection horizon:

- 7 days: collector stability only;
- 30 days: first forward Route C1 risk study;
- 90 days: stronger regime-aware Route C study;
- longer: preferred if storage and ops are manageable.

Do not stop this collector unless it is corrupting data or blocking higher-priority infrastructure.

Required live liquidation files:

- raw append-only liquidation events;
- 1m zero-filled aggregate;
- 5m aggregate;
- 1h compatibility aggregate;
- health summary.

## 7.2 Historical Binance Vision Snapshot Data

This data is still useful, but only as a proxy.

Known limitation:

- Binance liquidation snapshot is not complete liquidation tape;
- it is closer to largest force-order snapshot per symbol per second;
- it cannot be interpreted as total market liquidation notional.

Use it for:

- exploratory Route C1 price-risk study;
- event density estimation;
- pressure-label prototyping.

Do not use it for:

- final full-market liquidation-volume conclusions;
- strong live alpha claims;
- total liquidation notional interpretation.

## 7.3 Historical Orderbook Data

Orderbook data exists under:

```text
/Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook
```

Observed coverage:

- Binance and OKX;
- BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT;
- funding files also exist;
- approximately 74 daily files per exchange-symbol;
- observed BTC/ETH/SOL coverage around 2026-02-10 to 2026-05-08.

This is valuable for Route C, but a time-overlap audit is mandatory.

Potential uses:

1. If orderbook dates overlap liquidation events:
   - direct post-liquidation liquidity deterioration study.

2. If orderbook dates do not overlap liquidation events:
   - build normal liquidity baseline;
   - define spread/depth/impact metrics;
   - estimate execution-risk thresholds;
   - wait for forward liquidation + orderbook overlap.

Important normalization issue:

- Binance samples show deeper books, often around 20 levels in existing files.
- OKX examples may have fewer levels.
- Therefore, compare normalized metrics such as depth within bps and impact cost, not raw level count.

---

## 8. Lessons Reused From Failed Branches

## 8.1 From Extreme Funding

Reusable lessons:

- A strategy signal is not enough; it must survive funding, basis, fees, and execution friction.
- `depth_aware=false` was a major research limitation.
- Reject-reason distribution is useful and should be preserved.
- Funding is better used as context than as a forced standalone trigger.
- Shadow results must distinguish proxy research from live-executable evidence.

Route C reuse:

- Use funding as C3 context, not C1 trigger.
- Use orderbook depth to make C1 execution-aware.
- Output blocker distribution:
  - insufficient event density;
  - no matched baseline;
  - no orderbook overlap;
  - spread effect absent;
  - impact effect absent;
  - symbol instability;
  - month instability.

## 8.2 From Vol-Breakout

Reusable lessons:

- High volatility is dangerous even when it is not profitable.
- Hour-level exits hide sub-hour jump and stop-loss overrun risk.
- Sparse event density makes standalone alpha unattractive.
- Relaxing thresholds to manufacture trades usually worsens tail risk.

Route C reuse:

- Focus on MAE, jump risk, and adverse excursion.
- Measure risk windows at 1m/5m granularity, not only hourly closes.
- Treat high-vol windows as possible no-trade zones.
- Do not promote a signal just because median looks acceptable; inspect P75/P90/P95 tails.

---

## 9. Required Data For Route C

## 9.1 Minimum Data For C1 Price-Only Study

Required:

- 1m price bars;
- 1m liquidation aggregates;
- symbol;
- timestamp;
- liquidation side;
- liquidation notional proxy;
- zero-filled non-event minutes;
- matched baseline windows.

Can run without orderbook, but result is weaker.

## 9.2 Preferred Data For C1 Execution-Risk Study

Required:

- all minimum C1 data;
- orderbook snapshots;
- top-of-book bid/ask;
- depth levels;
- exchange;
- timestamp;
- funding rate optional;
- mark price optional.

Orderbook sampling target:

- 1 snapshot per second is enough for first Route C study;
- 100ms feed can be downsampled to 1s for storage and analysis;
- preserve raw daily files if storage allows.

## 9.3 Data For C2

Required:

- C1 liquidation aggregate;
- side-aware pressure;
- per-minute notional;
- price displacement during episode;
- post-episode price and liquidity metrics.

Preferred:

- event-level raw liquidation archive for dedup and side validation.

## 9.4 Data For C3

Required:

- C2 episode labels;
- funding context;
- OI context if available;
- pre-event return context;
- pre-event volatility context;
- orderbook imbalance context if available.

Preferred:

- walk-forward split by month;
- out-of-sample validation windows.

---

## 10. Server Data Collection Decision

## 10.1 Should The Liquidation Collector Continue?

Yes.

The liquidation collector should keep running because it is now producing the cleanest forward liquidation archive available to us.

Operational target:

- keep it running continuously;
- monitor raw row count;
- monitor invalid JSON lines;
- monitor 1m aggregate coverage;
- monitor 24h research readiness;
- preserve raw data as append-only evidence.

Minimum useful horizon:

- 30 days for first forward Route C1 study;
- 90 days for stronger regime study.

## 10.2 Should The Orderbook Collector Be Restarted?

Yes, but not blindly.

Before restarting, fix or confirm the retention policy.

Current project config shows:

```text
COLLECTOR_DATA_RETENTION_DAYS = 14
```

That is too short for research. If restarted with this setting, old orderbook files can be deleted during rotation, which is bad for Route C.

Recommended change before long-running collection:

- set retention to at least 90 days; or
- disable auto-delete and move cleanup to manual archive policy; or
- write to dated archive directories with checksum.

Recommended orderbook collection scope:

- Binance USDT perp: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT;
- OKX swaps: same symbols if bandwidth allows;
- 1s write interval is sufficient for first Route C;
- keep funding collection enabled;
- optionally collect ADA only if needed for old system continuity, not for Route C core.

## 10.3 What Else Should Be Collected?

Priority 1:

- live forceOrder raw events;
- 1m/5m zero-filled liquidation aggregates;
- Binance orderbook snapshots for the same symbols;
- price 1m bars for same symbols.

Priority 2:

- OKX orderbook snapshots for cross-exchange liquidity stress comparison;
- funding rate;
- mark price.

Priority 3:

- open interest;
- taker buy/sell volume;
- long/short account ratio if reliable vendor is available.

Do not overload the server with new data sources until C1 data overlap is confirmed.

---

## 11. Research Execution Order

### Batch 0: Data Overlap Audit

Goal:

- verify whether liquidation events and orderbook snapshots overlap in time.

Checks:

- liquidation raw earliest/latest timestamp;
- 1m aggregate earliest/latest timestamp;
- orderbook earliest/latest timestamp by exchange-symbol;
- overlap hours by symbol;
- missing orderbook days;
- missing liquidation days.

Decision:

- if overlap >= 7 days: start C1 paired study;
- if overlap < 7 days: continue collectors and only build metric adapters/baselines.

### Batch 1: C1 Price-Only Baseline

Goal:

- test whether liquidation events increase realized volatility, range, and MAE.

Why first:

- can run before orderbook overlap is sufficient;
- validates whether Route C has basic risk signal.

### Batch 2: C1 Orderbook-Aware Study

Goal:

- test whether spread, depth, and impact cost deteriorate after liquidation events.

This is the core Route C1 proof.

### Batch 3: C2 Episode Pressure

Goal:

- replace isolated 1m shock with multi-minute pressure labels.

Only run after C1 shows risk-filter value.

### Batch 4: C3 Context-Conditioned Directionality

Goal:

- test locked contexts for directional structure.

Only run after C1/C2 provide stable event labels and enough sample size.

---

## 12. Promotion Rules

Route C must not jump directly to live trading.

Promotion path:

1. Research summary passes C1 risk criteria.
2. Shadow-only filter is added.
3. System logs what trades would have been paused/reduced.
4. Compare blocked trades versus allowed trades.
5. Only after at least one scan cycle in shadow mode should the filter be considered for live gating.

Live-safe first action should be conservative:

- observe-only;
- then pause new entries;
- then reduce notional;
- only later modify execution mode.

Route C should never increase position size or net exposure in its first live integration.

---

## 13. Final Recommendation

Proceed with Route C in this order:

1. Keep liquidation collector running.
2. Restart orderbook collector only after retention/archive policy is made research-safe.
3. Run a data-overlap audit.
4. Build C1 price-only risk study.
5. Add orderbook-aware C1 once overlap exists.
6. Only then consider C2 episode labels.
7. Treat C3 as a later alpha branch, not the immediate next step.

The highest-value near-term deliverable is not a new trade entry.

The highest-value near-term deliverable is:

> a validated liquidation-aware execution risk filter that tells the system when not to trade normally.

---

## 14. C1 Hardening Addendum

External review correctly identified the largest weakness in the first draft:

> C1 is directionally correct, but the statistical contract was not hard enough.

This section locks the first implementation scope. Later variants must be treated as separate research branches, not silently mixed into Phase 1.

### 14.1 First-Version Event Algorithm

Do not support both 24h and 30d thresholds in the first pass.

First-version C1 event definition:

- `event_score = same-symbol same-side trailing 24h percentile rank`;
- `reference_window = previous 1440 1m bars`;
- exclude the current bar from the reference window;
- `event_threshold = percentile_rank >= 0.995`;
- require side-aware notional;
- require `dominance_ratio >= 0.65`;
- apply `min_abs_notional` by symbol tier:
  - BTC/ETH: major threshold from project config or research config;
  - SOL/XRP/DOGE: alt threshold from project config or research config;
- dedup by `symbol + side + 5m bucket`;
- keep only the largest-notional event inside the dedup bucket.

Do not add 30d thresholds, multiple percentile thresholds, or episode variants until this first C1 loop has a clean result.

### 14.2 Post-Event Window Anti-Leakage Rule

C1 measures risk **after** the liquidation event. It must not include the event minute or the 5m bar containing the event.

Definition:

- if `shock_bar_start = 12:03:00`;
- then `shock_bar_end = 12:03:59`;
- `first_post_1m_window = 12:04:00`;
- `first_complete_5m_response_bar = 12:05:00-12:09:59`.

All response metrics must start after the event is complete:

- 1m metrics start at the next minute;
- 5m bar metrics start at the next complete 5m bar;
- realized volatility, range, MAE, MFE, and orderbook deterioration must not include the event bar.

This prevents event-process movement from being mislabeled as future post-event risk.

### 14.3 Direction-Agnostic And Strategy-Conditioned Risk

C1 does not predict direction, so adverse excursion must be split into two metric families.

Direction-agnostic risk:

- `max_abs_excursion_bps`;
- `high_low_range_bps`;
- `realized_vol_bps`;
- `jump_return_abs_bps`.

Strategy-conditioned adverse excursion:

- `mae_if_long_bps = min(low / entry_price - 1, 0) * 10000`;
- `mae_if_short_bps = min(entry_price / high - 1, 0) * 10000`.

Required summary fields:

```json
{
  "max_abs_excursion_p90_bps": 0.0,
  "mae_if_long_p90_bps": 0.0,
  "mae_if_short_p90_bps": 0.0
}
```

This lets C1 support both generic no-trade risk and existing-strategy side-aware protection.

### 14.4 Matched Baseline Contract

Each event should attempt to match `K = 20` baseline windows.

Primary matching conditions:

1. same symbol;
2. same month;
3. same hour-of-day bucket, allowing `+-1h`;
4. pre-event 30m realized volatility percentile in the same 10% bucket;
5. no liquidation shock in the baseline window's previous 30m or next 30m;
6. no overlap with another event response window.

Fallback rules:

1. if no match, relax time-of-day first;
2. then relax volatility percentile to `+-20%`;
3. if still no match, mark event as `no_matched_baseline`;
4. unmatched events do not enter the main statistic.

Required summary fields:

```json
{
  "event_count": 100,
  "matched_event_count": 82,
  "unmatched_event_count": 18,
  "matched_baseline_count": 1640,
  "baseline_match_rate": 0.82
}
```

If `baseline_match_rate < 0.70`, C1 cannot pass.

### 14.5 Hard Pass / Fail Criteria

C1 price-only first-stage gate:

- `event_count >= 100`;
- `matched_event_count >= 70`;
- `baseline_match_rate >= 0.70`;
- `post_event_vol_ratio_median >= 1.5`;
- `post_event_range_ratio_median >= 1.4`;
- `post_event_abs_excursion_p90 / baseline_abs_excursion_p90 >= 1.3`;
- `symbols_passing >= 2` among BTC/ETH/SOL;
- `months_passing >= 2`;
- `max_single_symbol_event_share <= 0.60`;
- `max_single_month_event_share <= 0.60`.

C1 orderbook-aware gate:

- `spread_deterioration_ratio_median >= 1.2`;
- `impact_cost_500usdt_ratio_median >= 1.2`;
- `depth_within_10bps_ratio_median <= 0.8`;
- orderbook effect appears within 1/5/10m.

If price-only passes but orderbook-aware fails, the result is at most:

```text
volatility_warning
```

It must not be promoted to an execution filter.

### 14.6 Live Action Mapping

The first implementation must not rely on manual interpretation.

Recommended action mapping:

- `observe_only`:
  - price-only risk passes;
  - orderbook-aware evidence is not yet available or does not pass.

- `pause_entry`:
  - price-only risk passes;
  - spread or impact cost deterioration passes.

- `reduce_notional`:
  - `impact_cost_500usdt_ratio >= 1.2`; or
  - `depth_within_10bps_ratio <= 0.8`.

- `risk_off`:
  - `post_event_abs_excursion_p90 >= baseline * 2.0`;
  - `spread_deterioration_ratio >= 1.5`;
  - effect holds in at least 2 symbol/month groups.

First live-safe action must be:

```text
observe_only -> shadow pause_entry
```

Do not start with `force_taker_only_with_small_size`. If liquidity is deteriorating, forcing taker execution can mean actively crossing the spread at the worst moment.

### 14.7 Opportunity Cost And False Positive Check

Risk filters can destroy profitability by blocking good trades.

Shadow analysis must answer:

- how many existing scanner signals would have been filtered;
- how blocked signals performed;
- how allowed signals performed;
- how much signal frequency drops;
- whether main profitable trades were blocked.

Required proxy fields:

```json
{
  "filtered_time_share": 0.0,
  "filtered_signal_share_if_applied_to_existing_scanner": 0.0,
  "blocked_trade_proxy_count": 0,
  "allowed_trade_proxy_count": 0
}
```

If `filtered_time_share > 0.20`, treat the filter as high-risk until opportunity-cost analysis proves otherwise.

### 14.8 Orderbook Collection Hard Caps

Current server constraints matter:

- 2 CPU cores;
- 2GB RAM;
- about 30GB root disk;
- no planned disk expansion;
- weekly local archive and cleanup is the chosen operating mode.

Therefore, do not require 90-day server retention in the no-expansion mode.

No-expansion operating mode:

- server keeps short-term cache;
- local Mac archive stores long-term research data;
- `COLLECTOR_DATA_RETENTION_DAYS = 14`;
- weekly rsync + checksum + server cleanup;
- daily disk usage check;
- alert at 70% disk usage;
- hard intervention at 85% disk usage.

If resource pressure appears, reduce collection in this order:

1. stop ADA first;
2. stop OKX orderbook second;
3. retain Binance USDT perp BTC/ETH/SOL;
4. retain 1s write interval;
5. retain enough depth to compute 5/10/20bps depth and impact cost.

Staged rollout:

- Stage 1: Binance BTC/ETH/SOL only;
- Stage 2: add XRP/DOGE if disk and IO remain safe;
- Stage 3: add OKX only if cross-exchange liquidity comparison is needed.

### 14.9 Historical Binance Vision Snapshot Boundary

Binance Vision snapshot + kline data can only validate post-event **price risk**.

It cannot validate:

- spread deterioration;
- depth withdrawal;
- impact-cost deterioration;
- final live execution-risk filter behavior.

Reason:

- snapshot data has liquidation proxy and price bars;
- it does not have synchronized orderbook state.

Therefore:

- Binance Vision proxy can support C1 price-only exploration;
- final execution-filter evidence requires live overlap between liquidation archive and orderbook archive.

### 14.10 C2 And C3 Start Gates

C2 start gate:

- C1 price-only passes;
- `event_count >= 100`;
- at least 2 symbols pass;
- `baseline_match_rate >= 0.70`.

C3 start gate:

- C1 orderbook-aware passes; or
- C2 improves C1 metrics by at least 20%;
- each context bucket has at least 50 events;
- walk-forward split is available;
- estimated net edge after costs is positive.

Do not start C2/C3 before these gates. Otherwise Route C becomes another data-mining branch.

### 14.11 Revised Development Sequence

Do not build C1/C2/C3 together.

Batch 0: data overlap audit

Required output:

```json
{
  "liquidation_1m_zero_fill_coverage_24h": 0.0,
  "orderbook_snapshot_coverage_24h": 0.0,
  "price_1m_coverage_24h": 0.0,
  "overlap_hours_by_symbol": {},
  "ready_for_price_only": true,
  "ready_for_orderbook_aware": false
}
```

Batch 1: C1 price-only baseline

- event detection;
- matched baseline;
- realized volatility;
- range;
- max absolute excursion;
- MAE if long / MAE if short;
- month/symbol stability.

Batch 2: C1 orderbook-aware

- spread;
- depth within 5/10/20bps;
- impact cost 500/1000/2000 USDT;
- maker adverse-selection proxy.

Batch 3: shadow-only filter simulation

- `would_pause_entry`;
- `would_reduce_notional`;
- `would_increase_slippage_reserve`;
- compare blocked versus allowed posterior risk.

This keeps Route C scoped as a small research sprint, not a strategy rewrite.
