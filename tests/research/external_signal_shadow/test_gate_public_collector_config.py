from __future__ import annotations

from configs import base


def test_stage1_2_gate_config_is_public_readonly() -> None:
    assert base.EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL == "https://api.gateio.ws/api/v4"
    assert base.EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH == "/spot/tickers"
    assert base.EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS == (
        "BTC_USDT",
        "ETH_USDT",
        "SOL_USDT",
        "XRP_USDT",
        "DOGE_USDT",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_MAX_RETRIES >= 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_RETRY_BACKOFF_SEC >= 0
    assert base.EXTERNAL_SIGNAL_STAGE1_2_INTER_REQUEST_DELAY_SEC >= 0
    assert "readonly" in base.EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT.lower()
