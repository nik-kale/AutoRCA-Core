# MCP Integration Guide

AutoRCA-Core provides a Model Context Protocol (MCP) server that exposes RCA functionality as tools for Claude Desktop, Claude Code, and other MCP-compatible clients.

## Installation

Install AutoRCA-Core with MCP support:

```bash
pip install "autorca-core[mcp]"
```

Or install all optional dependencies:

```bash
pip install "autorca-core[all]"
```

## Claude Desktop Integration

### 1. Start the MCP Server

The MCP server uses stdio transport and is designed to be launched by Claude Desktop:

```bash
autorca mcp-server
```

### 2. Configure Claude Desktop

Add AutoRCA-Core to your Claude Desktop MCP configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "autorca": {
      "command": "autorca",
      "args": ["mcp-server"]
    }
  }
}
```

### 3. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the AutoRCA-Core tools.

## Available Tools

Once configured, Claude can use these tools:

### `run_rca`
Run comprehensive root cause analysis on observability data.

**Parameters:**
- `logs_path` (required): Path to log files
- `symptom` (required): Description of the incident
- `metrics_path` (optional): Path to metrics files
- `traces_path` (optional): Path to trace files
- `configs_path` (optional): Path to config change files
- `window_minutes` (optional): Analysis window in minutes (default: 60)
- `format` (optional): Output format - "markdown" or "json" (default: markdown)

**Example Claude prompt:**
```
Please analyze the logs in /var/log/app for the symptom "API returning 500 errors" 
using the metrics in /var/metrics
```

### `analyze_logs`
Analyze log files for anomalies and patterns.

**Parameters:**
- `logs_path` (required): Path to log files
- `time_from` (optional): Start time in ISO format
- `time_to` (optional): End time in ISO format
- `service_filter` (optional): Filter to specific service

**Example Claude prompt:**
```
Analyze the logs in /var/log/app from 2025-01-01T10:00:00 to 2025-01-01T11:00:00
```

### `get_service_graph`
Build and return the service dependency graph.

**Parameters:**
- `logs_path` (required): Path to log files
- `traces_path` (optional): Path to trace files (recommended for dependencies)
- `metrics_path` (optional): Path to metrics files

**Example Claude prompt:**
```
Show me the service dependency graph from the logs in /var/log/app and traces in /var/traces
```

### `find_root_causes`
Apply rule-based heuristics to find root cause candidates.

**Parameters:**
- `logs_path` (required): Path to log files
- `metrics_path` (optional): Path to metrics
- `traces_path` (optional): Path to traces
- `sensitivity` (optional): "strict", "normal", or "relaxed" (default: normal)

**Example Claude prompt:**
```
Find root causes in /var/log/app with strict sensitivity
```

## Example Workflows

### Incident Investigation
```
1. "Show me the service graph for the production logs"
2. "Analyze the logs for the last hour"
3. "Find root causes with normal sensitivity"
4. "Run full RCA for symptom: checkout API timeouts"
```

### Daily Health Check
```
1. "Analyze today's logs for any anomalies"
2. "Find any potential root causes in the last 24 hours"
```

### Post-Deployment Validation
```
1. "Get the service graph before and after the deployment"
2. "Run RCA on logs since the deployment started"
```

## Troubleshooting

### "MCP server requires the 'mcp' package"
Install the MCP optional dependency:
```bash
pip install "autorca-core[mcp]"
```

### Claude Desktop can't find the command
Ensure `autorca` is in your PATH:
```bash
which autorca  # macOS/Linux
where autorca  # Windows
```

If not found, use the full path in `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "autorca": {
      "command": "/full/path/to/autorca",
      "args": ["mcp-server"]
    }
  }
}
```

### Server not starting
Check the Claude Desktop logs:
- **macOS**: `~/Library/Logs/Claude/mcp*.log`
- **Windows**: `%APPDATA%\Claude\Logs\mcp*.log`

## Security Considerations

- The MCP server runs with the same permissions as Claude Desktop
- Ensure log files don't contain sensitive information
- Consider using read-only file paths
- Use the validation limits to prevent resource exhaustion

## Advanced Configuration

### With Virtual Environment

```json
{
  "mcpServers": {
    "autorca": {
      "command": "/path/to/venv/bin/autorca",
      "args": ["mcp-server"]
    }
  }
}
```

### With Custom Log Level

The MCP server respects the `AUTORCA_LOG_LEVEL` environment variable:

```json
{
  "mcpServers": {
    "autorca": {
      "command": "autorca",
      "args": ["mcp-server"],
      "env": {
        "AUTORCA_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Next Steps

- Explore the [main README](../README.md) for core AutoRCA concepts
- Check [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines
- Review example data in the `examples/` directory

