# AutoRCA-Core Architecture

## Overview

AutoRCA-Core (`autorca_core`) turns logs, metrics, traces and config-change events
into a service graph, detects incidents on it, and ranks root-cause candidates with
deterministic rules. An LLM can optionally rewrite the result as a narrative summary.
The CLI (`autorca`), the Python API (`run_rca`) and the MCP server all run the same
pipeline.

## Components

### 1. Ingestion (`autorca_core/ingestion/`)
- `load_logs`, `load_metrics`, `load_traces`, `load_configs` read a file or a
  directory (recursively) and normalize records into the models below.
- Formats: JSON Lines and plain-text logs; CSV/JSON/JSONL metrics; JSON/JSONL span
  records; JSON/JSONL/YAML config changes. Malformed records are skipped.
- Every timestamp is normalized to timezone-aware UTC (naive values are taken as UTC).
- `IngestionLimits` (in `validation.py`) caps file size, files per directory and
  total events, and skips files whose real path escapes the source directory.

### 2. Model (`autorca_core/model/`)
- Events: `LogEvent`, `MetricPoint`, `Span`, `ConfigChange`.
- Graph: `Service`, `Dependency`, `IncidentNode`, `ServiceGraph`.

### 3. Graph Engine (`autorca_core/graph_engine/`)
- `GraphBuilder` discovers services, infers dependencies from parent/child spans
  that cross services, and creates incidents: error spikes (logs and failed spans),
  latency spikes, CPU/memory exhaustion, and deployment/config changes.
- `GraphQueries` provides hotspots, the incident timeline and causal chains.

### 4. Reasoning (`autorca_core/reasoning/`)
- `rules.apply_rules` ranks candidates from five heuristics: changes followed by
  incidents, resource exhaustion, failing services with no failing dependencies,
  failing shared dependencies, and causal-chain roots. Duplicate
  (service, incident type) candidates are merged.
- `llm.AnthropicLLM` writes the summary with Claude; `DummyLLM` is the offline
  template and the fallback when an API call fails.
- `loop.run_rca` orchestrates ingestion, graph building, rules and summary.

### 5. Outputs (`autorca_core/outputs/`)
- Markdown, JSON and self-contained HTML reports (`save_report`). Text from the
  analysed data is HTML-escaped in HTML reports.

### 6. Interfaces
- CLI: `autorca quickstart`, `autorca run`, `autorca mcp-server`.
- MCP server (`autorca_core/mcp/`): see [MCP_INTEGRATION.md](MCP_INTEGRATION.md).

## Configuration

| Setting | Where it is read |
|---|---|
| `ThresholdConfig` (spike counts and windows, latency/resource thresholds, change-correlation window) | Passed to `run_rca(..., thresholds=...)`; presets `ThresholdConfig.strict()` / `.relaxed()` |
| `AUTORCA_ERROR_SPIKE_COUNT`, `AUTORCA_ERROR_SPIKE_WINDOW`, `AUTORCA_LATENCY_SPIKE_MS`, `AUTORCA_LATENCY_SPIKE_COUNT`, `AUTORCA_RESOURCE_EXHAUSTION_PERCENT`, `AUTORCA_RESOURCE_EXHAUSTION_COUNT`, `AUTORCA_CHANGE_CORRELATION_SECONDS` | `ThresholdConfig.from_env()` only; the CLI uses the defaults |
| `ANTHROPIC_API_KEY` | `AnthropicLLM` when no `api_key` is passed |
| `AUTORCA_LOG_LEVEL` | `autorca mcp-server` |
| `AUTORCA_MCP_ALLOWED_ROOTS` | `autorca mcp-server`; restricts which directories the tools may read |

## Extensibility Points

1. **Custom parsers**: add a loader under `autorca_core/ingestion/` that returns the
   model objects.
2. **Custom rules**: add a `_rule_*` function in `autorca_core/reasoning/rules.py`
   and call it from `apply_rules`.
3. **Custom LLMs**: implement the `LLMInterface` protocol in
   `autorca_core/reasoning/llm.py` and pass it as `run_rca(..., llm=...)`.
4. **Custom outputs**: add a generator in `autorca_core/outputs/reports.py`.
