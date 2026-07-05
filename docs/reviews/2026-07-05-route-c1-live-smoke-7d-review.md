# Route C1 Price-Only Proxy Precheck Review

> **IMPORTANT:** This proxy cannot promote to live filter (`can_promote_live_filter: false`).  
> Generalization allowed: `false`.  
> Data semantics: `snapshot_proxy_not_complete_liquidation_tape`.

## Run Mode

- `run_mode`: `live_smoke_7d`
- `data_source`: `binance_vision_liquidation_snapshot`

## Data Coverage

| Field | Value |
|---|---|
| events detected | 1536 |
| matched events | 904 |
| baseline match rate | 0.589 |
| sample_days | 23 |

## Price Risk Ratios (Event / Baseline Median)

| Metric | Value | Gate |
|---|---|---|
| post_event_vol_ratio_median | 1.551 | >= 1.5 |
| post_event_range_ratio_median | 1.693 | >= 1.4 |
| post_event_abs_excursion_p90_ratio | 3.806 | >= 1.3 |

post_event_vol_ratio_median
看的是 5 分钟 realized volatility 的中位数比值
1 表示事件后波动比正常更大
你这里是 1.55，说明事件后波动明显放大

post_event_range_ratio_median
看的是 5 分钟 high-low range 的中位数比值
1 表示 K 线实体/上下影的振幅比正常更大
你这里是 1.69，说明区间明显放大

post_event_abs_excursion_p90_ratio
看的是绝对偏离的 90 分位比值
它更偏向看“尾部最极端的那部分”
你这里是 3.81，说明极端偏离很强
## Proxy Kill-Switch

- `proxy_kill_switch_weak`: `false`
  - vol_ratio < 1.2: False
  - range_ratio < 1.2: False
  - excursion_p90_ratio < 1.1: False

## Event Distribution

### By Symbol

- `BTCUSDT`: 305
- `ETHUSDT`: 291
- `SOLUSDT`: 308

### By Month

- `2026-05`: 42
- `2026-06`: 852
- `2026-07`: 10

## Decision

```
decision: route_c1_baseline_match_failed
```
baseline_match_rate 不是单纯由“采集时间长短”决定
它主要取决于：

事件样本分布是否均匀
baseline 候选池是否足够大
symbol / month / hour / vol bucket 是否能配得上
是否有足够多的完整未来 5m 窗口
为什么 baseline 比例不能太低
因为这个脚本不是只看“事件后指标高不高”，而是看：

事件后指标是否稳定地高于“相近正常样本”

如果 baseline 太少、太偏，容易出现两个问题：

结果偶然性变大

少数能匹配上的 baseline 可能刚好不代表正常分布
解释力下降

你不能很有底气地说“事件后确实比正常更强”
只能说“在少数能匹配上的样本里看起来更强”
这就是为什么 baseline_match_rate 会被拿来当门槛，而不是装饰字段。

## Next Path

- Ratios below gate thresholds. Continue 7d live overlap collection.
- Run `audit_route_c1_data_overlap.py --mode live_overlap` after 7 days.

## Anti-Leakage Contract

- Entry price = `first_response_row[open_price]` (first complete 5m response bar).
- Response window excludes the shock bar and any partial 5m bar containing it.
- Baseline matched windows must have zero liquidation in candidate + ±30m guard + future 5m.

## Algorithm Parameters

```json
{
  "ROUTE_C1_EVENT_PERCENTILE_THRESHOLD": 0.995,
  "ROUTE_C1_REQUIRED_REFERENCE_BARS": 1440,
  "ROUTE_C1_DOMINANCE_RATIO_MIN": 0.65,
  "ROUTE_C1_DEDUP_BUCKET_MINUTES": 5,
  "ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT": 50000.0,
  "ROUTE_C1_ALT_ABS_THRESHOLD_USDT": 10000.0,
  "ROUTE_C1_BASELINE_MATCH_COUNT": 20,
  "ROUTE_C1_BASELINE_MATCH_RATE_MIN": 0.7,
  "ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX": 1.2,
  "ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX": 1.2,
  "ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX": 1.1
}
```
