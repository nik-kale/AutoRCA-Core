import argparse
import json
from pathlib import Path

from .config import RCAConfig
from .ingestion.file_loader import load_jsonl
from .parsing.log_parser import normalize_event
from .reasoning.heuristics import simple_grouping
from .reasoning.agent import analyze_incident
from .reporting.formatter import format_human_readable

def main() -> None:
    parser = argparse.ArgumentParser(description="ADAPT-RCA CLI")
    parser.add_argument("--input", required=True, help="Path to JSONL log file")
    parser.add_argument("--output", help="Path to write JSON result")
    args = parser.parse_args()

    config = RCAConfig()  # future use

    raw_events = list(load_jsonl(args.input))
    events = [normalize_event(e) for e in raw_events]

    incident_groups = simple_grouping(events)
    # For now, treat all events as one incident
    result = analyze_incident(incident_groups[0] if incident_groups else [])

    print(format_human_readable(result))

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
