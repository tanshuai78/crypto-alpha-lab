import argparse
import json
from pathlib import Path

from src.research.external_signal_shadow.models import (
    load_events_jsonl,
    load_price_bars_jsonl,
)
from src.research.external_signal_shadow.replay import run_stage0_shadow_replay
from src.research.external_signal_shadow.summary import decide_stage0_shadow_replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--price-bars", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--external-api", action="store_true")
    args = parser.parse_args(argv)

    if args.external_api:
        return 1

    try:
        events = load_events_jsonl(args.events)
        bars = load_price_bars_jsonl(args.price_bars)
    except (OSError, ValueError, json.JSONDecodeError):
        return 1

    summary = decide_stage0_shadow_replay(run_stage0_shadow_replay(events, bars))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Written: {output_path}")
    print(f"  decision: {summary['decision']}")
    print(f"  failure_type: {summary['failure_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
