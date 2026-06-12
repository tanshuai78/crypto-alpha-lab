import pytest


def test_canonical_json_hash_ignores_dict_order_and_fetched_at_wrapper():
    from src.research.external_signal_shadow.safety import canonical_json_hash

    left = {"b": 2, "a": {"z": 1, "y": 2}}
    right = {"a": {"y": 2, "z": 1}, "b": 2}

    assert canonical_json_hash(left) == canonical_json_hash(right)


def test_canonical_json_hash_does_not_include_fetched_at_when_hashing_raw_payload():
    from src.research.external_signal_shadow.safety import canonical_json_hash

    raw_payload = {"token": "ABC", "score": 1.0}
    wrapper_1 = {"fetched_at_ms": 1000, "raw_payload": raw_payload}
    wrapper_2 = {"fetched_at_ms": 2000, "raw_payload": raw_payload}

    assert canonical_json_hash(wrapper_1["raw_payload"]) == canonical_json_hash(
        wrapper_2["raw_payload"]
    )


def test_forbidden_policy_rejects_exact_secret_keys():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    with pytest.raises(ValueError, match="private_key"):
        validate_no_executable_payload({"safe": {"private_key": "0xdead"}})


def test_forbidden_policy_rejects_path_patterns():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    with pytest.raises(ValueError, match="swap.calldata"):
        validate_no_executable_payload({"swap": {"calldata": "0xabc"}})


def test_forbidden_policy_allows_analytics_keys():
    from src.research.external_signal_shadow.safety import validate_no_executable_payload

    validate_no_executable_payload(
        {
            "tx_count": 12,
            "tx_hash": "0xabc",
            "swap_count_24h": 7,
            "orderbook_imbalance": 0.12,
            "orderbook_depth_usd": 1_000_000,
        }
    )
