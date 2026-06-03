# -*- coding: utf-8 -*-
from __future__ import annotations


def test_route_c1_config_exports_required_thresholds():
    import configs.base as cfg

    assert cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD == 0.995
    assert cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS == 1440
    assert cfg.ROUTE_C1_DOMINANCE_RATIO_MIN == 0.65
    assert cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES == 5
    assert cfg.ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT == 50_000.0
    assert cfg.ROUTE_C1_ALT_ABS_THRESHOLD_USDT == 10_000.0
    assert cfg.ROUTE_C1_BASELINE_MATCH_COUNT == 20
    assert cfg.ROUTE_C1_BASELINE_MATCH_RATE_MIN == 0.70


def test_route_c1_proxy_weak_thresholds_are_explicit():
    import configs.base as cfg

    assert cfg.ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX == 1.2
    assert cfg.ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX == 1.2
    assert cfg.ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX == 1.1
