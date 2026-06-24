import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5c1_price_coverage_expansion import main


def test_review_states_coverage_only_and_no_alpha(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_sparse_inconclusive",
        "stage1_5b_symbol_events": 194,
        "futures_coverage_pass_event_count": 12,
        "spot_proxy_available_event_count": 40,
        "blockers": ["futures_coverage_density_insufficient"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    args = [
        "review_stage1_5c1_price_coverage_expansion.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()
    content = review.read_text()
    assert "Stage 1.5C.1" in content
    assert "coverage-only" in content
    assert "futures_coverage_density_insufficient" in content
    assert "paper_trading_allowed" in content
    assert "live_trading_allowed" in content
    assert "alpha_interpretation_allowed" in content
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in content
