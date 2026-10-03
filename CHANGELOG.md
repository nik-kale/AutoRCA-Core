# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed
- `import autorca_core` failed with a `SyntaxError`: merge conflict markers had
  been committed in `ingestion/logs.py` and `reasoning/loop.py`.
- Log ingestion dropped every line, because `LogEvent` could not be constructed
  without an explicit `event_type`.
- Comparing naive and timezone-aware datetimes crashed the README library example,
  `autorca run --from/--to` without an offset, the MCP `analyze_logs` tool and
  traces with epoch timestamps. All timestamps are now normalized to UTC; naive
  values are treated as UTC.
- Config directories never loaded (unsupported brace glob); single-record JSON and
  one-line JSONL files were silently dropped; non-object JSON records aborted a
  whole load; an explicit `duration_ms` was rescaled as if it were microseconds;
  spans with a non-numeric status code were dropped.
- `IngestionLimits` is enforced by every loader: the file limit spans all file
  patterns, the total-event cap holds, and a symlink pointing outside the source
  directory is skipped instead of aborting the load.
- Error spikes are detected within a sliding window, so an earlier stray error no
  longer hides a burst; span-based detection honors `ThresholdConfig`;
  deployments are no longer blamed for incidents that started before them;
  causal-chain ordering uses each service's earliest incident; duplicate
  candidates for the same service and incident type are merged.
- `AnthropicLLM` crashed on any graph with dependencies, defaulted to a retired
  model, and read only the first content block. It now falls back to the
  rule-based summary when the API call fails, and does not retry non-retryable
  errors.
- HTML reports escape text taken from the analysed data (log messages, service
  names, symptom), closing a stored XSS; the service graph canvas grows with the
  number of services instead of clipping nodes.
- `autorca run` writes only the report to stdout, so `--format json` output can be
  redirected to a file; passing only one of `--from`/`--to` is an error.
- `get_logger()` no longer resets a configured log level, logger names are no
  longer double-prefixed, and `structured=True` emits valid JSON.
- `DataSourcesConfig` is exported from the package root, as the README shows.
- The `py.typed` marker declared in the package data is now shipped.

### Added
- `AUTORCA_MCP_ALLOWED_ROOTS` confines MCP tool file access to the listed
  directories. The MCP server also honors `AUTORCA_LOG_LEVEL`, as documented.
- Optional `limits` argument on `load_metrics`, `load_traces` and `load_configs`.
- `AnthropicLLM(input_cost_per_mtok=..., output_cost_per_mtok=...)` for cost
  estimates.

### Changed
- `AnthropicLLM` defaults to `claude-sonnet-5-5` with `max_tokens=16000`.
- The `mcp` extra requires `mcp>=1.0`.
- CI selects ruff rules explicitly, bounds black to the 26.x style, and also tests
  Python 3.13.

### Removed
- The unpackaged `src/adapt_rca` prototype and its tests.
- `requirements.txt`, which had drifted from `pyproject.toml` (install with
  `pip install -e ".[dev]"`).
