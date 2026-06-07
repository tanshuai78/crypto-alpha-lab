from __future__ import annotations

from typing import Any


def stage0_current_tradable_bias_contract() -> dict[str, Any]:
    """Return the static bias contract for Stage 0."""
    return {
        "universe_scope": "current_tradable_universe_only",
        "survivorship_bias_control": "not_controlled",
        "delisted_symbols_included": False,
        "result_usage": "hypothesis_screening_only_not_final_evidence",
    }
