import argparse
import json
from pathlib import Path

from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--price-map", required=True)
    parser.add_argument("--output-events", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--external-api", action="store_true")
    args = parser.parse_args(argv)

    if args.external_api:
        return 1

    try:
        summary = run_file_backed_connector(
            input_files=args.input,
            price_map_path=args.price_map,
            output_path=args.output_events,
            source=args.source,
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return 1

    output_summary = Path(args.output_summary)
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"Written events: {args.output_events}")
    print(f"Written summary: {args.output_summary}")
    print(f"  decision: {summary['decision']}")
    print(f"  failure_type: {summary['failure_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
