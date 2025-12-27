"""
MCP server implementation for AutoRCA-Core.

Provides MCP tools for:
- Running RCA on observability data
- Analyzing logs for anomalies
- Querying service topology
- Finding root cause candidates
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from autorca_core.reasoning.loop import run_rca_from_files, DataSourcesConfig, run_rca
from autorca_core.outputs.reports import generate_markdown_report, generate_json_report
from autorca_core.ingestion import load_logs, load_metrics, load_traces
from autorca_core.graph_engine.builder import build_service_graph
from autorca_core.reasoning.rules import apply_rules
from autorca_core.config import ThresholdConfig
from autorca_core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def create_mcp_server():
    """
    Create and configure the MCP server with AutoRCA-Core tools.

    Returns:
        Configured MCP server instance
    """
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
    except ImportError:
        raise ImportError(
            "mcp package required for MCP server. Install with: pip install mcp"
        )

    server = Server("autorca-core")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available AutoRCA-Core tools."""
        return [
            Tool(
                name="run_rca",
                description=(
                    "Run comprehensive root cause analysis on observability data. "
                    "Analyzes logs, metrics, and traces to identify root causes of incidents. "
                    "Returns a detailed RCA report with candidates ranked by confidence."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "logs_path": {
                            "type": "string",
                            "description": "Path to log files (directory or file)",
                        },
                        "symptom": {
                            "type": "string",
                            "description": "Description of the incident symptom",
                        },
                        "metrics_path": {
                            "type": "string",
                            "description": "Optional path to metrics files",
                        },
                        "traces_path": {
                            "type": "string",
                            "description": "Optional path to trace files",
                        },
                        "configs_path": {
                            "type": "string",
                            "description": "Optional path to config change files",
                        },
                        "window_minutes": {
                            "type": "integer",
                            "description": "Analysis window in minutes (default: 60)",
                            "default": 60,
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format (default: markdown)",
                            "default": "markdown",
                        },
                    },
                    "required": ["logs_path", "symptom"],
                },
            ),
            Tool(
                name="analyze_logs",
                description=(
                    "Analyze log files for anomalies and patterns. "
                    "Detects error spikes, unusual patterns, and service issues. "
                    "Returns summary of findings with timestamps and affected services."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "logs_path": {
                            "type": "string",
                            "description": "Path to log files (directory or file)",
                        },
                        "time_from": {
                            "type": "string",
                            "description": "Start time in ISO format (optional)",
                        },
                        "time_to": {
                            "type": "string",
                            "description": "End time in ISO format (optional)",
                        },
                        "service_filter": {
                            "type": "string",
                            "description": "Filter to specific service (optional)",
                        },
                    },
                    "required": ["logs_path"],
                },
            ),
            Tool(
                name="get_service_graph",
                description=(
                    "Build and return the service dependency graph from observability data. "
                    "Shows which services depend on each other and detected incidents. "
                    "Returns JSON representation of the service topology."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "logs_path": {
                            "type": "string",
                            "description": "Path to log files",
                        },
                        "traces_path": {
                            "type": "string",
                            "description": "Optional path to trace files (recommended for dependencies)",
                        },
                        "metrics_path": {
                            "type": "string",
                            "description": "Optional path to metrics files",
                        },
                    },
                    "required": ["logs_path"],
                },
            ),
            Tool(
                name="find_root_causes",
                description=(
                    "Apply rule-based heuristics to find root cause candidates. "
                    "Uses graph analysis, temporal correlation, and pattern matching. "
                    "Returns ranked list of candidates with confidence scores and evidence."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "logs_path": {
                            "type": "string",
                            "description": "Path to log files",
                        },
                        "metrics_path": {
                            "type": "string",
                            "description": "Optional path to metrics",
                        },
                        "traces_path": {
                            "type": "string",
                            "description": "Optional path to traces",
                        },
                        "sensitivity": {
                            "type": "string",
                            "enum": ["strict", "normal", "relaxed"],
                            "description": "Detection sensitivity (default: normal)",
                            "default": "normal",
                        },
                    },
                    "required": ["logs_path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        logger.info(f"MCP tool called: {name} with args: {arguments}")

        try:
            if name == "run_rca":
                result = await _handle_run_rca(arguments)
            elif name == "analyze_logs":
                result = await _handle_analyze_logs(arguments)
            elif name == "get_service_graph":
                result = await _handle_get_service_graph(arguments)
            elif name == "find_root_causes":
                result = await _handle_find_root_causes(arguments)
            else:
                result = f"Unknown tool: {name}"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error(f"Error in tool {name}: {e}", exc_info=True)
            error_msg = f"Error executing {name}: {str(e)}"
            return [TextContent(type="text", text=error_msg)]

    return server


async def _handle_run_rca(args: Dict[str, Any]) -> str:
    """Handle run_rca tool call."""
    logs_path = args["logs_path"]
    symptom = args["symptom"]
    metrics_path = args.get("metrics_path")
    traces_path = args.get("traces_path")
    configs_path = args.get("configs_path")
    window_minutes = args.get("window_minutes", 60)
    output_format = args.get("format", "markdown")

    logger.info(f"Running RCA for symptom: {symptom}")

    # Run RCA
    result = run_rca_from_files(
        logs_path=logs_path,
        metrics_path=metrics_path,
        traces_path=traces_path,
        configs_path=configs_path,
        primary_symptom=symptom,
        window_minutes=window_minutes,
    )

    # Generate report
    if output_format == "json":
        return generate_json_report(result)
    else:
        return generate_markdown_report(result)


async def _handle_analyze_logs(args: Dict[str, Any]) -> str:
    """Handle analyze_logs tool call."""
    logs_path = args["logs_path"]
    time_from_str = args.get("time_from")
    time_to_str = args.get("time_to")
    service_filter = args.get("service_filter")

    # Parse times
    time_from = datetime.fromisoformat(time_from_str) if time_from_str else None
    time_to = datetime.fromisoformat(time_to_str) if time_to_str else None

    logger.info(f"Analyzing logs from: {logs_path}")

    # Load logs
    logs = load_logs(logs_path, time_from, time_to, service_filter)

    # Analyze
    total_logs = len(logs)
    error_logs = [log for log in logs if log.is_error()]
    services = set(log.service for log in logs)

    # Build summary
    summary_parts = [
        "# Log Analysis Summary",
        "",
        f"**Total Logs:** {total_logs}",
        f"**Error Logs:** {len(error_logs)} ({len(error_logs)/max(total_logs,1)*100:.1f}%)",
        f"**Unique Services:** {len(services)}",
        "",
    ]

    if time_from and time_to:
        summary_parts.append(f"**Time Range:** {time_from.isoformat()} to {time_to.isoformat()}")
        summary_parts.append("")

    if services:
        summary_parts.append("**Services Detected:**")
        for service in sorted(services):
            service_errors = len([log for log in error_logs if log.service == service])
            summary_parts.append(f"- {service}: {service_errors} errors")
        summary_parts.append("")

    if error_logs:
        summary_parts.append("**Recent Errors:**")
        for log in sorted(error_logs, key=lambda x: x.timestamp, reverse=True)[:10]:
            summary_parts.append(f"- [{log.timestamp.isoformat()}] {log.service}: {log.message[:100]}")

    return "\n".join(summary_parts)


async def _handle_get_service_graph(args: Dict[str, Any]) -> str:
    """Handle get_service_graph tool call."""
    logs_path = args["logs_path"]
    traces_path = args.get("traces_path")
    metrics_path = args.get("metrics_path")

    logger.info("Building service graph")

    # Load data
    logs = load_logs(logs_path) if logs_path else []
    traces = load_traces(traces_path) if traces_path else []
    metrics = load_metrics(metrics_path) if metrics_path else []

    # Build graph
    graph = build_service_graph(logs=logs, metrics=metrics, traces=traces)

    # Convert to JSON
    graph_dict = graph.to_dict()
    return json.dumps(graph_dict, indent=2, default=str)


async def _handle_find_root_causes(args: Dict[str, Any]) -> str:
    """Handle find_root_causes tool call."""
    logs_path = args["logs_path"]
    metrics_path = args.get("metrics_path")
    traces_path = args.get("traces_path")
    sensitivity = args.get("sensitivity", "normal")

    logger.info(f"Finding root causes with sensitivity: {sensitivity}")

    # Configure thresholds based on sensitivity
    if sensitivity == "strict":
        thresholds = ThresholdConfig.strict()
    elif sensitivity == "relaxed":
        thresholds = ThresholdConfig.relaxed()
    else:
        thresholds = ThresholdConfig()

    # Load data
    logs = load_logs(logs_path) if logs_path else []
    metrics = load_metrics(metrics_path) if metrics_path else []
    traces = load_traces(traces_path) if traces_path else []

    # Build graph and find candidates
    graph = build_service_graph(logs=logs, metrics=metrics, traces=traces, thresholds=thresholds)
    candidates = apply_rules(graph, thresholds=thresholds)

    # Format results
    result_parts = [
        "# Root Cause Candidates",
        "",
        f"**Total Candidates:** {len(candidates)}",
        f"**Sensitivity:** {sensitivity}",
        "",
    ]

    for i, candidate in enumerate(candidates[:10], 1):
        result_parts.append(f"## {i}. {candidate.service}")
        result_parts.append(f"**Type:** {candidate.incident_type.value}")
        result_parts.append(f"**Confidence:** {candidate.confidence:.0%}")
        result_parts.append(f"**Explanation:** {candidate.explanation}")
        result_parts.append("")
        result_parts.append("**Evidence:**")
        for evidence in candidate.evidence[:5]:
            result_parts.append(f"- {evidence}")
        result_parts.append("")

    return "\n".join(result_parts)


def start_mcp_server():
    """Start the MCP server (stdio transport)."""
    configure_logging(level="INFO")
    logger.info("Starting AutoRCA-Core MCP server")

    server = create_mcp_server()

    try:
        from mcp.server.stdio import stdio_server
    except ImportError:
        raise ImportError(
            "mcp package required. Install with: pip install mcp"
        )

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run())

