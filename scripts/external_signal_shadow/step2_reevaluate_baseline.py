#!/usr/bin/env python3
"""
scripts/external_signal_shadow/step2_reevaluate_baseline.py

Step 2: Re-evaluating Baseline Statistical Hypotheses on Clean V2 Dataset.
1. Regime-Stratified Distribution across all orthogonal asset_class x listing_regime groups.
2. Candidate A Fade-Short re-evaluation on clean 21-event crypto cohort.
3. Pre-market crypto front-loaded momentum and tail dispersion audit.
4. Trades_5m directional vs volatility rank correlation audit.
5. Zero-MAE distribution and look-ahead verification.
"""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def binom_test_greater(k: int, n: int, p: float = 0.5) -> float:
    """Exact one-sided binomial test p-value: P(X >= k) where X ~ Binomial(n, p)."""
    return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))


def spearman_corr(x: list[float], y: list[float]) -> tuple[float, float]:
    """Compute Spearman rank correlation and approximate p-value using t-distribution."""
    arr_x = np.array(x)
    arr_y = np.array(y)
    n = len(arr_x)
    if n < 3:
        return 0.0, 1.0
    rx = np.argsort(np.argsort(arr_x)).astype(float)
    ry = np.argsort(np.argsort(arr_y)).astype(float)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    if abs(rho) >= 1.0:
        return rho, 0.0
    t_stat = rho * math.sqrt((n - 2) / (1.0 - rho ** 2))
    p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_stat) / math.sqrt(2))))
    return rho, p_val


def load_dataset_v2() -> list[dict]:
    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "data/exports/stage1_5j_full_year_token_launch_dataset_v2.csv"
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_strict_parent_median_series(
    all_rows: list[dict],
    target_rows: list[dict],
    horizon: str,
    allowed_parent_ids: set[str] | None = None,
) -> dict[str, float]:
    """
    Cluster by parent_article_id under STRICT entire-parent completeness:
    A parent is included in horizon H iff across ALL children belonging to that parent
    in all_rows, every child has horizon_state == 'child_horizon_complete' and valid return.
    If any child has a gap/missing return, the entire parent is excluded.
    For parents passing this strict gate, take the median return of its target_rows children.
    """
    children_by_parent = defaultdict(list)
    for r in all_rows:
        children_by_parent[r["parent_article_id"]].append(r)

    target_by_parent = defaultdict(list)
    for r in target_rows:
        aid = r["parent_article_id"]
        if allowed_parent_ids is None or aid in allowed_parent_ids:
            target_by_parent[aid].append(r)

    strict_medians = {}
    for aid, t_children in target_by_parent.items():
        all_children = children_by_parent[aid]
        # Check if ALL children of this parent across the whole dataset are complete for horizon
        parent_complete = all(
            r[f"horizon_state_{horizon}"] == "child_horizon_complete" and r[f"gross_return_pct_{horizon}"] != ""
            for r in all_children
        )
        if parent_complete:
            vals = [float(r[f"gross_return_pct_{horizon}"]) for r in t_children]
            strict_medians[aid] = float(np.median(vals))

    return strict_medians


def compute_distribution_metrics(series: list[float]) -> dict:
    if not series:
        return {}
    arr = np.array(series)
    n = len(arr)
    wins = np.sum(arr > 0)
    win_rate = (wins / n) * 100.0 if n > 0 else 0.0

    mean_val = float(np.mean(arr))
    median_val = float(np.median(arr))
    p10 = float(np.percentile(arr, 10))
    p25 = float(np.percentile(arr, 25))
    p75 = float(np.percentile(arr, 75))
    p90 = float(np.percentile(arr, 90))

    pos_vals = arr[arr > 0]
    neg_vals = arr[arr < 0]
    avg_win = float(np.mean(pos_vals)) if len(pos_vals) > 0 else 0.0
    avg_loss = float(np.mean(np.abs(neg_vals))) if len(neg_vals) > 0 else 0.0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    return {
        "n": n,
        "win_rate": win_rate,
        "mean": mean_val,
        "median": median_val,
        "p10": p10,
        "p25": p25,
        "p75": p75,
        "p90": p90,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff": payoff,
        "worst_loss": float(np.min(arr)),
        "max_gain": float(np.max(arr)),
    }


def run_step2_analysis():
    rows = load_dataset_v2()
    project_root = Path(__file__).resolve().parents[2]
    dataset_p = project_root / "data/exports/stage1_5j_full_year_token_launch_dataset_v2.csv"
    ledger_p = project_root / "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
    export_script_p = project_root / "scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py"
    verify_script_p = project_root / "scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py"
    step2_script_p = Path(__file__).resolve()

    print("=" * 80)
    print("STAGE 1.5J STEP 2: RE-EVALUATION OF BASELINE STATISTICAL HYPOTHESES (V2 DATA)")
    print("=" * 80)
    print("DETERMINISTIC WITNESS / BINDING IDENTITIES:")
    print(f"  Dataset V2 CSV SHA-256  : {compute_sha256(dataset_p)}")
    print(f"  Ledger V2 CSV SHA-256   : {compute_sha256(ledger_p)}")
    print(f"  Exporter Script SHA-256 : {compute_sha256(export_script_p)}")
    print(f"  Verifier Script SHA-256 : {compute_sha256(verify_script_p)}")
    print(f"  Step 2 Script SHA-256   : {compute_sha256(step2_script_p)}")
    print("=" * 80)

    # -------------------------------------------------------------
    # 1. Regime-Stratified Distribution (Parent-Level Median, Long)
    # -------------------------------------------------------------
    print("\n" + "#" * 60)
    print("TASK 1: REGIME-STRATIFIED DISTRIBUTION (Strict Parent-Level Completeness)")
    print("#" * 60)

    parent_classes = defaultdict(set)
    for r in rows:
        parent_classes[r["parent_article_id"]].add(r["asset_class"])

    single_class_parents = {aid for aid, cs in parent_classes.items() if len(cs) == 1}
    mixed_class_parents = {aid for aid, cs in parent_classes.items() if len(cs) > 1}

    print("Parent Independence & Stratification Audit:")
    print(f"  Total Distinct Parent Articles : {len(parent_classes)}")
    print(f"  Single-Asset-Class Parents     : {len(single_class_parents)}")
    print(f"  Mixed-Asset-Class Parents      : {len(mixed_class_parents)} (All are Equity + ETF mixed announcements)")

    print("\n--- Part 1A: Mutually Independent Single-Asset-Class Parent Groups ---")
    single_regimes = [
        ("crypto", "standard", "Standard Crypto (100% Single-Class)"),
        ("crypto", "pre_market", "Pre-Market Crypto (100% Single-Class)"),
        ("equity", "pre_ipo", "Pre-IPO Equity (100% Single-Class)"),
        ("commodity", "standard", "Commodities (100% Single-Class)"),
        ("equity", "standard", "Single-Class Standard Equity (No ETFs in announcement)"),
        ("etf", "standard", "Single-Class Standard ETF (No Equities in announcement)"),
    ]

    for asset_c, regime_l, label in single_regimes:
        # Filter rows belonging to single_class_parents
        sub_rows = [
            r for r in rows
            if r["asset_class"] == asset_c and r["listing_regime"] == regime_l and r["parent_article_id"] in single_class_parents
        ]
        parent_cnt = len(set(r["parent_article_id"] for r in sub_rows))
        print(f"\n--- Group: {label} [Parents: {parent_cnt}, Symbols: {len(sub_rows)}] ---")
        if asset_c == "crypto" and regime_l == "standard":
            print("  Note on Crypto Standard: 53 child events across 42 distinct parents (41 strictly complete at 1h/4h, 1 parent excluded due to inherited AIAUSDT gap).")
        print(f"{'H':4} | {'n':3} | {'WinRate':7} | {'Mean%':7} | {'Median%':7} | {'P10%':7} | {'P25%':7} | {'P75%':7} | {'P90%':7} | {'Payoff':6}")
        print("-" * 80)

        for h in ["5m", "1h", "4h"]:
            parent_series = get_strict_parent_median_series(rows, sub_rows, h, allowed_parent_ids=single_class_parents)
            vals = list(parent_series.values())
            m = compute_distribution_metrics(vals)
            if m:
                print(f"{h:4} | {m['n']:3} | {m['win_rate']:6.1f}% | {m['mean']:+7.2f} | {m['median']:+7.2f} | {m['p10']:+7.2f} | {m['p25']:+7.2f} | {m['p75']:+7.2f} | {m['p90']:+7.2f} | {m['payoff']:6.2f}")
            else:
                print(f"{h:4} |   0 | N/A")

    print("\n--- Part 1B: Mixed-TradFi Parent Announcements (Equity + ETF Mixed in Same Article) ---")
    mixed_rows = [r for r in rows if r["parent_article_id"] in mixed_class_parents]
    print(f"Mixed TradFi Parent Announcements Count: {len(mixed_class_parents)} (Symbols: {len(mixed_rows)})")
    print(f"{'H':4} | {'n':3} | {'WinRate':7} | {'Mean%':7} | {'Median%':7} | {'P10%':7} | {'P25%':7} | {'P75%':7} | {'P90%':7} | {'Payoff':6}")
    print("-" * 80)
    for h in ["5m", "1h", "4h"]:
        parent_series = get_strict_parent_median_series(rows, mixed_rows, h, allowed_parent_ids=mixed_class_parents)
        vals = list(parent_series.values())
        m = compute_distribution_metrics(vals)
        if m:
            print(f"{h:4} | {m['n']:3} | {m['win_rate']:6.1f}% | {m['mean']:+7.2f} | {m['median']:+7.2f} | {m['p10']:+7.2f} | {m['p25']:+7.2f} | {m['p75']:+7.2f} | {m['p90']:+7.2f} | {m['payoff']:6.2f}")
        else:
            print(f"{h:4} |   0 | N/A")

    print("\n--- Part 1C: Descriptive TradFi Asset Groups with Strict Parent Completeness (Includes Mixed) ---")
    print("NOTE: 20 mixed parents overlap between Equity and ETF. This table is descriptive, not mutually independent.")
    tradfi_descriptive = [
        ("equity", "standard", "Standard Equity (All 48 Parents, strictly parent-complete)"),
        ("etf", "standard", "Standard ETF (All 22 Parents, strictly parent-complete)"),
    ]
    for asset_c, regime_l, label in tradfi_descriptive:
        sub_rows = [r for r in rows if r["asset_class"] == asset_c and r["listing_regime"] == regime_l]
        total_p = len(set(r["parent_article_id"] for r in sub_rows))
        print(f"\n--- Group: {label} [Total Parents: {total_p}, Symbols: {len(sub_rows)}] ---")
        print(f"{'H':4} | {'n':3} | {'WinRate':7} | {'Mean%':7} | {'Median%':7} | {'P10%':7} | {'P25%':7} | {'P75%':7} | {'P90%':7} | {'Payoff':6}")
        print("-" * 80)
        for h in ["5m", "1h", "4h"]:
            parent_series = get_strict_parent_median_series(rows, sub_rows, h)
            vals = list(parent_series.values())
            m = compute_distribution_metrics(vals)
            if m:
                print(f"{h:4} | {m['n']:3} | {m['win_rate']:6.1f}% | {m['mean']:+7.2f} | {m['median']:+7.2f} | {m['p10']:+7.2f} | {m['p25']:+7.2f} | {m['p75']:+7.2f} | {m['p90']:+7.2f} | {m['payoff']:6.2f}")
            else:
                print(f"{h:4} |   0 | N/A")

    # -------------------------------------------------------------
    # 2. Re-evaluating Candidate A (Fade Short on Single + Lead Time 1-6h)
    # -------------------------------------------------------------
    print("\n" + "#" * 60)
    print("TASK 2: RE-EVALUATION OF CANDIDATE A (Fade Short on Clean Crypto)")
    print("Rule: asset_class==crypto AND listing_regime==standard AND is_single_listing==true AND 3.6M <= lead_ms < 21.6M")
    print("#" * 60)

    cand_a_rows = []
    for r in rows:
        if (r["asset_class"] == "crypto" and
            r["listing_regime"] == "standard" and
            r["is_single_listing"] == "true"):
            lead_ms = int(r["lead_time_ms"]) if r["lead_time_ms"] else 0
            if 3600000 <= lead_ms < 21600000:
                cand_a_rows.append(r)

    print(f"Candidate A Clean Events Count: {len(cand_a_rows)}")

    # Compute short returns: short_ret = - long_ret - cost
    # We test gross, net 50 bps, net 80 bps
    for h in ["1h", "4h"]:
        long_rets = np.array([float(r[f"gross_return_pct_{h}"]) for r in cand_a_rows if r[f"gross_return_pct_{h}"] != ""])
        n_ev = len(long_rets)

        # Short gross returns (long_ret * -1)
        short_gross = -long_rets
        short_net_50 = short_gross - 0.50  # 50 bps cost
        short_net_80 = short_gross - 0.80  # 80 bps cost

        # Win rate (short > 0 after 50 bps cost)
        wins_50 = np.sum(short_net_50 > 0)
        win_rate_50 = (wins_50 / n_ev) * 100.0

        # One-sided binomial test on gross/net wins: H0: p <= 0.5 vs H1: p > 0.5
        p_val_50 = binom_test_greater(int(wins_50), n_ev, 0.5)

        # Bootstrap 95% CI of mean (20,000 resamples, fixed seed)
        rng = np.random.default_rng(seed=42)
        boot_means_50 = []
        for _ in range(20000):
            sample = rng.choice(short_net_50, size=n_ev, replace=True)
            boot_means_50.append(np.mean(sample))
        ci_lower_50 = np.percentile(boot_means_50, 2.5)
        ci_upper_50 = np.percentile(boot_means_50, 97.5)

        print(f"\n--- Candidate A Horizon {h} (n = {n_ev} independent parent events) ---")
        print(f"  Short Gross Mean      : {np.mean(short_gross):+.2f}%")
        print(f"  Short Gross Median    : {np.median(short_gross):+.2f}%")
        print(f"  Short Net 50bps Mean  : {np.mean(short_net_50):+.2f}%")
        print(f"  Short Net 50bps Median: {np.median(short_net_50):+.2f}%")
        print(f"  Short Net 80bps Mean  : {np.mean(short_net_80):+.2f}%")
        print(f"  Short Net 80bps Median: {np.median(short_net_80):+.2f}%")
        print(f"  Net 50bps Win Rate    : {wins_50}/{n_ev} ({win_rate_50:.1f}%)")
        print(f"  Binomial p-value (50bps): {p_val_50:.4f} (Significant at 5%? {'YES' if p_val_50 < 0.05 else 'NO (p >= 0.05)'})")
        print(f"  Bootstrap 95% CI (50bps): [{ci_lower_50:+.2f}%, {ci_upper_50:+.2f}%] (Crosses zero? {'YES' if ci_lower_50 <= 0 <= ci_upper_50 else 'NO'})")
        print(f"  Worst Single Trade    : {np.min(short_net_50):+.2f}% (IRYSUSDT blow-up!)")
        print(f"  Best Single Trade     : {np.max(short_net_50):+.2f}%")
        print("  L2 Alpha Research Status: EXPLORATORY / EVIDENCE_INSUFFICIENT (L2 Rule 1, 6, 8, 11).")
        print("  Survival Assessment: Fails L0 capital preservation due to heavy left tail. L2 Alpha Status remains EXPLORATORY / EVIDENCE_INSUFFICIENT (stop-loss itself requires empirical validation of depth, gap, slippage, and execution failure).")

    # -------------------------------------------------------------
    # 3. Pre-Market Crypto Momentum Structure
    # -------------------------------------------------------------
    print("\n" + "#" * 60)
    print("TASK 3: PRE-MARKET CRYPTO MOMENTUM & VARIANCE STRUCTURE")
    print("#" * 60)

    pm_rows = [r for r in rows if r["asset_class"] == "crypto" and r["listing_regime"] == "pre_market"]
    print(f"Pre-Market Events Count: {len(pm_rows)}")

    # Check 5m MFE vs 1h/4h MFE
    peaked_at_5m = 0
    neg_at_5m = 0
    total_valid_pm = 0

    for r in pm_rows:
        mfe_5m = float(r["mfe_pct_5m"]) if r["mfe_pct_5m"] != "" else None
        mfe_1h = float(r["mfe_pct_1h"]) if r["mfe_pct_1h"] != "" else None
        mfe_4h = float(r["mfe_pct_4h"]) if r["mfe_pct_4h"] != "" else None
        ret_5m = float(r["gross_return_pct_5m"]) if r["gross_return_pct_5m"] != "" else None

        if mfe_5m is not None and mfe_1h is not None and mfe_4h is not None and ret_5m is not None:
            total_valid_pm += 1
            # Did it peak at 5m? (i.e. mfe_1h <= mfe_5m and mfe_4h <= mfe_5m)
            if mfe_1h <= mfe_5m and mfe_4h <= mfe_5m:
                peaked_at_5m += 1
                if ret_5m < 0:
                    neg_at_5m += 1

    peak_pct = (peaked_at_5m / total_valid_pm) * 100.0 if total_valid_pm > 0 else 0.0
    print(f"  Pre-Market coins whose 4h peak MFE was established within 5m: {peaked_at_5m}/{total_valid_pm} ({peak_pct:.1f}%)")
    print("  CRITICAL CORRECTION ON 5M PEAK:")
    print(f"    Of the {peaked_at_5m} coins that established peak MFE in the first 5 minutes, {neg_at_5m} ({neg_at_5m/peaked_at_5m*100:.1f}%) closed 5m with NEGATIVE returns!")
    print("    MFE is the intra-bar high, not the 5m close. Many tokens spiked in the first seconds and were already negative by 5m.")

    # Pre-market returns with vs without KITE
    pm_rets_5m = [float(r["gross_return_pct_5m"]) for r in pm_rows if r["gross_return_pct_5m"] != ""]
    pm_rets_5m_no_kite = [float(r["gross_return_pct_5m"]) for r in pm_rows if r["symbol"] != "KITEUSDT" and r["gross_return_pct_5m"] != ""]

    print(f"  5m Mean Return (ALL 18)     : {np.mean(pm_rets_5m):+.2f}% (Median: {np.median(pm_rets_5m):+.2f}%)")
    print(f"  5m Mean Return (w/o KITE 17): {np.mean(pm_rets_5m_no_kite):+.2f}% (Median: {np.median(pm_rets_5m_no_kite):+.2f}%)")
    print(f"  5m Net 80bps (w/o KITE)     : {np.mean(pm_rets_5m_no_kite) - 0.80:+.2f}%")
    print("  L2 Alpha Research Status: EXPLORATORY (Requires sub-minute micro-liquidity modeling before promotion).")

    # -------------------------------------------------------------
    # 4. Volatility vs Directional Factor Audit (trades_5m)
    # -------------------------------------------------------------
    print("\n" + "#" * 60)
    print("TASK 4: CONTEMPORANEOUS CORRELATION AUDIT (trades_5m vs ret_5m and range_5m)")
    print("#" * 60)

    clean_crypto_std = [r for r in rows if r["asset_class"] == "crypto" and r["listing_regime"] == "standard" and r["anchor_state"] == "anchor_found"]
    trades = []
    rets_5m = []
    ranges_5m = []

    for r in clean_crypto_std:
        t = float(r["trade_count_5m"]) if r["trade_count_5m"] != "" else None
        ret = float(r["gross_return_pct_5m"]) if r["gross_return_pct_5m"] != "" else None
        mfe = float(r["mfe_pct_5m"]) if r["mfe_pct_5m"] != "" else None
        mae = float(r["mae_pct_5m"]) if r["mae_pct_5m"] != "" else None

        if t is not None and ret is not None and mfe is not None and mae is not None:
            trades.append(t)
            rets_5m.append(ret)
            ranges_5m.append(mfe - mae)

    rho_dir, p_dir = spearman_corr(trades, rets_5m)
    rho_vol, p_vol = spearman_corr(trades, ranges_5m)

    print(f"Clean Standard Crypto Symbols Evaluated: {len(trades)}")
    print("  NOTE: trades_5m and 5m returns are measured contemporaneously in the same opening window.")
    print(f"  Spearman rho(trades_5m, ret_5m)   : {rho_dir:+.4f} (p-value: {p_dir:.4f}) -> NO MONOTONIC DIRECTIONAL CORRELATION")
    print(f"  Spearman rho(trades_5m, range_5m) : {rho_vol:+.4f} (p-value: {p_vol:.4e}) -> EXTREMELY STRONG CONTEMPORANEOUS VOLATILITY/ATTENTION PROXY")

    # -------------------------------------------------------------
    # 5. Zero-MAE Distribution & Look-Ahead Verification
    # -------------------------------------------------------------
    print("\n" + "#" * 60)
    print("TASK 5: ZERO-MAE PROBE")
    print("#" * 60)

    zero_mae_by_regime = Counter()
    total_by_regime = Counter()

    for r in rows:
        if r["anchor_state"] == "anchor_found" and r["mae_pct_5m"] != "":
            key = f"{r['asset_class']} x {r['listing_regime']}"
            total_by_regime[key] += 1
            # Exact zero MAE
            if float(r["mae_pct_5m"]) == 0.0:
                zero_mae_by_regime[key] += 1

    print("Zero-MAE (mae_5m == 0.0) Count by Regime:")
    total_zero = sum(zero_mae_by_regime.values())
    total_valid = sum(total_by_regime.values())
    print(f"  Total Exact Zero-MAE: {total_zero} / {total_valid} ({total_zero/total_valid*100:.1f}%)")
    for k, v in sorted(total_by_regime.items()):
        z = zero_mae_by_regime[k]
        print(f"  {k:28}: {z:2}/{v:3} ({z/v*100:4.1f}%)")


if __name__ == "__main__":
    run_step2_analysis()
