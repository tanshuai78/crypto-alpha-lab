import hashlib
import json

HARD_REJECT_EXACT_KEYS = {
    "private_key",
    "seed",
    "mnemonic",
    "signature",
    "signed_tx",
    "raw_tx",
    "api_key",
    "secret",
    "password",
    "passphrase",
    "order_request",
    "swap_request",
    "transfer_request",
    "wallet_seed",
    "wallet_private_key",
    "tx_payload",
}

HARD_REJECT_PATH_PATTERNS = {
    "wallet.private_key",
    "wallet.seed",
    "transaction.signed_payload",
    "transaction.raw_tx",
    "order.intent",
    "order.request",
    "swap.calldata",
    "swap.request",
    "transfer.request",
}

ALLOWED_ANALYTICS_KEYS = {
    "tx_count",
    "tx_hash",
    "swap_count_24h",
    "orderbook_imbalance",
    "orderbook_depth_usd",
}


def canonical_json_dumps(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_json_hash(payload: object) -> str:
    return hashlib.sha256(canonical_json_dumps(payload).encode("utf-8")).hexdigest()


def validate_no_executable_payload(payload: object) -> None:
    _walk(payload, path=())


def _walk(value: object, path: tuple[str, ...]) -> None:
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            child_path = (*path, key)
            dotted = ".".join(child_path)
            if key in HARD_REJECT_EXACT_KEYS and key not in ALLOWED_ANALYTICS_KEYS:
                raise ValueError(f"forbidden executable field: {dotted}")
            if dotted in HARD_REJECT_PATH_PATTERNS:
                raise ValueError(f"forbidden executable field: {dotted}")
            _walk(child, child_path)
    elif isinstance(value, list) or isinstance(value, tuple):
        for item in value:
            _walk(item, path)
