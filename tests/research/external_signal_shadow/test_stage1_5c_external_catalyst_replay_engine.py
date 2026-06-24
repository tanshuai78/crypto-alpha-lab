from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_engine import (
    compute_signed_net_return_bps,
    replay_candidates,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
)


def test_compute_signed_net_return_long_and_short():
    assert compute_signed_net_return_bps(100.0, 101.0, signed_direction=1, cost_bps=50) == 50.0
    assert compute_signed_net_return_bps(100.0, 101.0, signed_direction=-1, cost_bps=50) == -150.0


def test_replay_candidates_uses_entry_and_exit_open_prices():
    candidate = ExternalCatalystReplayCandidate(
        symbol_event_id="s1",
        event_type="exchange_delisting_notice",
        signed_mode="delisting_avoid_long_or_signed_short_diagnostic",
        signed_direction=-1,
        symbol="ABCUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=100.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    price_index = {"ABCUSDT": [
        {"bar_start_ms": 3_600_000, "open": 100.0},
        {"bar_start_ms": 18_000_000, "open": 95.0},
    ]}
    rows = replay_candidates([candidate], price_index, forward_windows_hours=(4,), cost_scenarios_bps=(50,))
    assert rows[0].long_gross_return_bps == -500.0
    assert rows[0].signed_gross_return_bps == 500.0
    assert rows[0].net_return_bps == 450.0


def test_replay_engine_does_not_cross_symbol_paths():
    abc = ExternalCatalystReplayCandidate(
        symbol_event_id="abc1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="ABCUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=100.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    xyz = ExternalCatalystReplayCandidate(
        symbol_event_id="xyz1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="XYZUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=200.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    price_index = {
        "ABCUSDT": [
            {"bar_start_ms": 3_600_000, "open": 100.0},
            {"bar_start_ms": 18_000_000, "open": 110.0},
        ],
        "XYZUSDT": [
            {"bar_start_ms": 3_600_000, "open": 200.0},
            {"bar_start_ms": 18_000_000, "open": 100.0},
        ],
    }
    rows = replay_candidates([abc, xyz], price_index, forward_windows_hours=(4,), cost_scenarios_bps=(50,))
    by_symbol = {r.symbol: r.net_return_bps for r in rows}
    assert by_symbol["ABCUSDT"] == 950.0
    assert by_symbol["XYZUSDT"] == -5050.0
