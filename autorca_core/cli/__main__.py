"""
AutoRCA-Core CLI: Command-line interface for running RCA.

Usage:
    autorca quickstart                              # Run quickstart example
    autorca run --logs ./logs --symptom "API 500s" # Run RCA on custom data
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

from autorca_core.reasoning.loop import run_rca, run_rca_from_files, DataSourcesConfig
from autorca_core.outputs.reports import generate_markdown_report, save_report
from autorca_core.logging import configure_logging


def run_mcp_server():
    """Start the MCP server."""
    try:
        from autorca_core.mcp.server import start_mcp_server
        start_mcp_server()
    except ImportError:
        print("Error: MCP server requires the 'mcp' package.")
        print("Install with: pip install 'autorca-core[mcp]'")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="autorca",
        description="AutoRCA-Core: Agentic Root Cause Analysis for Autonomous Reliability & Ops",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Quickstart command
    quickstart_parser = subparsers.add_parser(
        "quickstart",
        help="Run quickstart example with synthetic data",
    )
    
    # MCP server command
    mcp_parser = subparsers.add_parser(
        "mcp-server",
        help="Start MCP server for Claude Desktop integration",
    )
    quickstart_parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO)",
    )
    quickstart_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all logging output",
    )

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run RCA on custom data",
    )
    run_parser.add_argument(
        "--logs",
        type=str,
        required=True,
        help="Path to logs directory or file",
    )
    run_parser.add_argument(
        "--metrics",
        type=str,
        help="Path to metrics directory or file",
    )
    run_parser.add_argument(
        "--traces",
        type=str,
        help="Path to traces directory or file",
    )
    run_parser.add_argument(
        "--configs",
        type=str,
        help="Path to config changes directory or file",
    )
    run_parser.add_argument(
        "--from",
        dest="time_from",
        type=str,
        help="Start time (ISO format: 2025-11-10T10:00:00Z)",
    )
    run_parser.add_argument(
        "--to",
        dest="time_to",
        type=str,
        help="End time (ISO format: 2025-11-10T10:05:00Z)",
    )
    run_parser.add_argument(
        "--symptom",
        type=str,
        default="Unknown incident",
        help="Primary symptom description (e.g., 'Checkout API 500 errors')",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        help="Output file path for report (default: print to stdout)",
    )
    run_parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    run_parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO)",
    )
    run_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all logging output",
    )

    args = parser.parse_args()

    # Configure logging
    if hasattr(args, 'quiet') and args.quiet:
        configure_logging(level="CRITICAL")
    elif hasattr(args, 'log_level'):
        configure_logging(level=args.log_level)
    else:
        configure_logging(level="INFO")

    if args.command == "quickstart":
        run_quickstart()
    elif args.command == "run":
        run_custom_rca(args)
    elif args.command == "mcp-server":
        run_mcp_server()
    else:
        parser.print_help()
        sys.exit(1)


def run_quickstart():
    """Run the quickstart example with bundled synthetic data."""
    print("=" * 80)
    print("AutoRCA-Core Quickstart Example")
    print("=" * 80)
    print()

    # Find the examples directory
    examples_dir = Path(__file__).parent.parent.parent / "examples" / "quickstart_local_logs"

    if not examples_dir.exists():
        print(f"Error: Examples directory not found: {examples_dir}")
        print("Please run this command from the repository root or ensure examples are installed.")
        sys.exit(1)

    logs_file = examples_dir / "logs.jsonl"
    metrics_file = examples_dir / "metrics.jsonl"

    if not logs_file.exists():
        print(f"Error: Example logs not found: {logs_file}")
        sys.exit(1)

    print(f"Loading example data from: {examples_dir}")
    print()

    try:
        # Run RCA on the example data
        result = run_rca_from_files(
            logs_path=str(logs_file),
            metrics_path=str(metrics_file) if metrics_file.exists() else None,
            primary_symptom="Database connection exhaustion causing API errors",
            window_minutes=10,
        )

        # Generate and print report
        report = generate_markdown_report(result)
        print(report)

        print()
        print("=" * 80)
        print("Quickstart completed successfully!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Try running RCA on your own data:")
        print("   autorca run --logs /path/to/logs --symptom 'Your symptom here'")
        print()
        print("2. Check the full documentation:")
        print("   https://github.com/nik-kale/AutoRCA-Core")
        print()

    except Exception as e:
        print(f"Error running quickstart: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_custom_rca(args):
    """Run RCA on custom data."""
    print("=" * 80)
    print("AutoRCA-Core: Running RCA")
    print("=" * 80)
    print()

    # Validate inputs
    logs_path = Path(args.logs)
    if not logs_path.exists():
        print(f"Error: Logs path not found: {logs_path}")
        sys.exit(1)

    # Parse time window if provided
    time_from = None
    time_to = None

    if args.time_from and args.time_to:
        try:
            time_from = datetime.fromisoformat(args.time_from.replace('Z', '+00:00'))
            time_to = datetime.fromisoformat(args.time_to.replace('Z', '+00:00'))
            print(f"Time window: {time_from} to {time_to}")
        except ValueError as e:
            print(f"Error parsing time window: {e}")
            sys.exit(1)
    else:
        print("No time window specified - will analyze all data")

    print()

    try:
        # Run RCA
        if time_from and time_to:
            sources = DataSourcesConfig(
                logs_dir=args.logs,
                metrics_dir=args.metrics,
                traces_dir=args.traces,
                configs_dir=args.configs,
            )
            result = run_rca((time_from, time_to), args.symptom, sources)
        else:
            result = run_rca_from_files(
                logs_path=args.logs,
                metrics_path=args.metrics,
                traces_path=args.traces,
                configs_path=args.configs,
                primary_symptom=args.symptom,
            )

        # Generate report
        if args.output:
            save_report(result, args.output, format=args.format)
        else:
            # Print to stdout
            if args.format == "markdown":
                print(generate_markdown_report(result))
            elif args.format == "json":
                from autorca_core.outputs.reports import generate_json_report
                print(generate_json_report(result))
            else:
                from autorca_core.outputs.reports import generate_html_report
                print(generate_html_report(result))

        print()
        print("=" * 80)
        print("RCA completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"Error running RCA: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
