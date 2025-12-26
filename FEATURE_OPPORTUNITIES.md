# AutoRCA-Core: Feature Opportunities Analysis

> **Analysis Date:** 2025-12-26
> **Repository Version:** 0.2.0
> **Codebase Size:** ~2,800 lines of Python

---

## Executive Summary

This analysis identifies 8 high-impact feature opportunities for AutoRCA-Core, prioritized by value-to-effort ratio. The recommendations focus on immediate usability improvements, security hardening, and completing promised functionality.

---

## Priority Summary Table

| # | Feature | Category | Effort | Value | Priority Score |
|---|---------|----------|--------|-------|----------------|
| 1 | Fix File Glob Pattern Bug | Code Quality | Low | High | 3.0 |
| 2 | Replace print() with Structured Logging | Observability | Low | High | 3.0 |
| 3 | Implement Anthropic Claude LLM Integration | Functional | Medium | High | 1.5 |
| 4 | Add Configurable Detection Thresholds | Functional | Low | Medium | 2.0 |
| 5 | Add Input Validation and Size Limits | Security | Medium | High | 1.5 |
| 6 | Implement Interactive HTML Reports | Functional | Medium | High | 1.5 |
| 7 | Add CI/CD Pipeline with Test Coverage | Architecture | Low | Medium | 2.0 |
| 8 | Create MCP Server Implementation | Functional | High | High | 1.0 |

---

## Detailed Feature Specifications

---

### Feature #1: Fix File Glob Pattern Bug

**Category:** Code Quality
**Effort:** Low | **Value:** High | **Priority Score:** 3.0

#### Problem Statement

The file loading functions in ingestion modules use invalid Python glob patterns. The pattern `"**/*.{log,jsonl,txt}"` uses shell-style brace expansion which Python's `pathlib.glob()` does not support, causing silent failures when loading files from directories.

**Affected Files:**
- `autorca_core/ingestion/logs.py:45` - `"**/*.{log,jsonl,txt}"`
- `autorca_core/ingestion/metrics.py:47` - `"**/*.{csv,jsonl,json}"`
- `autorca_core/ingestion/traces.py:46` - `"**/*.{jsonl,json}"`

#### Proposed Solution

1. Replace single brace-expanded patterns with multiple explicit glob calls
2. Use a helper function to consolidate file discovery logic
3. Add test coverage for directory-based file loading

```python
# Before (broken)
for file_path in source_path.glob("**/*.{log,jsonl,txt}"):
    events.extend(_load_log_file(file_path))

# After (working)
extensions = ['*.log', '*.jsonl', '*.txt']
for ext in extensions:
    for file_path in source_path.glob(f"**/{ext}"):
        events.extend(_load_log_file(file_path))
```

#### Success Metrics
- All file types in directories are correctly discovered and loaded
- Unit tests verify loading from directories with mixed file types
- Zero data loss when processing multi-file directories

---

### Feature #2: Replace print() with Structured Logging

**Category:** Observability
**Effort:** Low | **Value:** High | **Priority Score:** 3.0

#### Problem Statement

The codebase uses `print()` statements for all output, including warnings, errors, and progress information. This makes it impossible to:
- Control log verbosity in library usage
- Filter or route logs in production
- Correlate logs with trace context
- Parse logs programmatically

**Example occurrences:** 27 `print()` calls across the codebase.

#### Proposed Solution

1. Create a logging configuration module at `autorca_core/logging.py`
2. Replace all `print()` calls with appropriate log levels:
   - Progress messages → `logger.info()`
   - Warnings → `logger.warning()`
   - Errors → `logger.error()`
3. Add structured context (service, file path, line number) to log messages
4. Allow users to configure log level via CLI flag `--log-level` or environment variable

```python
# logging.py
import logging
import sys

def configure_logging(level: str = "INFO", structured: bool = False):
    """Configure AutoRCA logging."""
    logger = logging.getLogger("autorca_core")
    logger.setLevel(getattr(logging, level.upper()))

    if structured:
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(module)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
```

#### Success Metrics
- Zero `print()` statements in production code paths
- Library users can silence output by configuring log level
- Logs include structured context for debugging
- CLI supports `--log-level` and `--quiet` flags

---

### Feature #3: Implement Anthropic Claude LLM Integration

**Category:** Functional Enhancement
**Effort:** Medium | **Value:** High | **Priority Score:** 1.5

#### Problem Statement

The `AnthropicLLM` class in `autorca_core/reasoning/llm.py` is a stub that raises `NotImplementedError`. This blocks one of the core value propositions: LLM-enhanced RCA summaries and remediation suggestions. The scaffolding exists but implementation is missing.

#### Proposed Solution

1. Implement the `AnthropicLLM` class with proper API integration
2. Create a well-engineered system prompt for RCA summarization
3. Implement retry logic with exponential backoff for API failures
4. Add token counting and cost estimation
5. Support streaming responses for long summaries

```python
class AnthropicLLM:
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def summarize_rca(self, graph, candidates, primary_symptom) -> str:
        system_prompt = """You are an expert SRE analyzing a production incident.
        Given the service graph, detected incidents, and root cause candidates,
        provide a clear, actionable summary that includes:
        1. Executive summary (2-3 sentences)
        2. Most likely root cause with confidence level
        3. Evidence supporting the conclusion
        4. Recommended remediation steps
        5. What to monitor to verify the fix"""

        user_prompt = self._build_rca_prompt(graph, candidates, primary_symptom)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
```

#### Success Metrics
- LLM-enhanced summaries provide actionable remediation steps
- API errors are handled gracefully with fallback to DummyLLM
- Token usage is logged for cost tracking
- Integration tests verify Anthropic API interaction

---

### Feature #4: Add Configurable Detection Thresholds

**Category:** Functional Enhancement
**Effort:** Low | **Value:** Medium | **Priority Score:** 2.0

#### Problem Statement

Anomaly detection uses hardcoded thresholds that may not suit all environments:
- Error spike: 3+ errors in 5 minutes (`builder.py:159,167`)
- Latency spike: >1000ms (`builder.py:199`)
- Resource exhaustion: >90% (`builder.py:212`)
- Recent change correlation: 10 minutes (`rules.py:118`)

Different systems have vastly different baselines, making these thresholds inappropriate for many use cases.

#### Proposed Solution

1. Create a `ThresholdConfig` dataclass with sensible defaults
2. Allow threshold configuration via:
   - Constructor parameters
   - Environment variables
   - Configuration file (YAML/JSON)
3. Add CLI flags for common threshold overrides
4. Document threshold tuning in the README

```python
@dataclass
class ThresholdConfig:
    """Configurable thresholds for anomaly detection."""
    # Error detection
    error_spike_count: int = 3
    error_spike_window_seconds: int = 300

    # Latency detection
    latency_spike_ms: float = 1000.0
    latency_spike_count: int = 2

    # Resource detection
    resource_exhaustion_percent: float = 90.0
    resource_exhaustion_count: int = 2

    # Correlation windows
    change_correlation_seconds: int = 600

    @classmethod
    def from_env(cls) -> "ThresholdConfig":
        """Load thresholds from environment variables."""
        return cls(
            error_spike_count=int(os.getenv("AUTORCA_ERROR_SPIKE_COUNT", 3)),
            latency_spike_ms=float(os.getenv("AUTORCA_LATENCY_SPIKE_MS", 1000)),
            # ... etc
        )
```

#### Success Metrics
- Users can tune thresholds without code changes
- CLI includes `--latency-threshold`, `--error-count` flags
- Documentation includes threshold tuning guide
- Different presets available (e.g., "strict", "relaxed")

---

### Feature #5: Add Input Validation and Size Limits

**Category:** Security
**Effort:** Medium | **Value:** High | **Priority Score:** 1.5

#### Problem Statement

The ingestion layer lacks security controls that could lead to:
1. **Path traversal:** No validation that file paths stay within expected directories
2. **Resource exhaustion:** No limits on file sizes, line counts, or memory usage
3. **Deprecated APIs:** Uses `datetime.utcnow()` which is deprecated in Python 3.12+
4. **Error exposure:** Raw exception messages may leak sensitive path information

#### Proposed Solution

1. **Path validation:** Ensure all file paths resolve within the specified source directory
2. **Size limits:** Add configurable limits for files and total data ingested
3. **Memory guards:** Use streaming/chunked processing for large files
4. **Timezone-aware datetimes:** Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`
5. **Safe error messages:** Sanitize exceptions before displaying to users

```python
# Path validation
def _validate_path(source_path: Path, file_path: Path) -> bool:
    """Ensure file_path is within source_path (prevent traversal)."""
    try:
        file_path.resolve().relative_to(source_path.resolve())
        return True
    except ValueError:
        return False

# Size limits
@dataclass
class IngestionLimits:
    max_file_size_mb: float = 100.0
    max_total_events: int = 1_000_000
    max_line_length: int = 65536

def _check_file_size(file_path: Path, limits: IngestionLimits) -> None:
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > limits.max_file_size_mb:
        raise ValueError(f"File exceeds size limit: {size_mb:.1f}MB > {limits.max_file_size_mb}MB")
```

#### Success Metrics
- Path traversal attacks are blocked with clear error messages
- Large files are rejected or processed in chunks
- No `datetime.utcnow()` deprecation warnings
- Security review passes without critical findings

---

### Feature #6: Implement Interactive HTML Reports

**Category:** Functional Enhancement
**Effort:** Medium | **Value:** High | **Priority Score:** 1.5

#### Problem Statement

The current HTML report (`outputs/reports.py:152-194`) simply wraps the markdown output in a `<pre>` tag, providing no interactivity or visualization. The roadmap promises "Interactive HTML reports with graph visualizations" but this is not implemented.

#### Proposed Solution

1. Generate proper semantic HTML with CSS styling (no external dependencies)
2. Add SVG-based service graph visualization using D3.js-style layout
3. Create collapsible sections for evidence and remediation
4. Add an interactive timeline view for incidents
5. Include copy-to-clipboard functionality for evidence

```python
def generate_html_report(result: RCARunResult) -> str:
    """Generate an interactive HTML report with visualizations."""
    # Inline CSS for portable reports
    css = """
    <style>
        .service-graph { /* SVG graph styles */ }
        .timeline { /* Incident timeline styles */ }
        .collapsible { cursor: pointer; }
        .evidence { display: none; }
        .evidence.active { display: block; }
    </style>
    """

    # Generate SVG service graph
    graph_svg = _generate_service_graph_svg(result.service_graph)

    # Generate timeline
    timeline_html = _generate_timeline_html(result.timeline)

    # JavaScript for interactivity (inline, no dependencies)
    js = """
    <script>
        document.querySelectorAll('.collapsible').forEach(el => {
            el.addEventListener('click', () => {
                el.nextElementSibling.classList.toggle('active');
            });
        });
    </script>
    """

    return f"""<!DOCTYPE html>
    <html><head>{css}</head>
    <body>
        <h1>RCA Report: {result.primary_symptom}</h1>
        <section class="graph">{graph_svg}</section>
        <section class="timeline">{timeline_html}</section>
        <section class="analysis">{_generate_analysis_html(result)}</section>
        {js}
    </body></html>
    """
```

#### Success Metrics
- HTML reports are self-contained (no external dependencies)
- Service graph visualization shows dependencies and incident markers
- Timeline is interactive with hover details
- Reports render correctly in modern browsers (Chrome, Firefox, Safari)

---

### Feature #7: Add CI/CD Pipeline with Test Coverage

**Category:** Architecture & Scalability
**Effort:** Low | **Value:** Medium | **Priority Score:** 2.0

#### Problem Statement

The project lacks continuous integration, making it difficult to:
- Ensure code quality on every change
- Track test coverage over time
- Validate compatibility across Python versions
- Automate releases

Currently there are only 4 test files with minimal coverage.

#### Proposed Solution

1. Add GitHub Actions workflow for CI
2. Configure pytest with coverage reporting
3. Add code quality checks (ruff, mypy, black)
4. Create release automation workflow
5. Add coverage badge to README

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run linting
        run: |
          ruff check .
          black --check .
          mypy autorca_core

      - name: Run tests with coverage
        run: pytest --cov=autorca_core --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

#### Success Metrics
- All PRs require passing CI checks
- Test coverage is tracked and reported (target: >80%)
- Code style is enforced automatically
- Python 3.10, 3.11, and 3.12 are verified working

---

### Feature #8: Create MCP Server Implementation

**Category:** Functional Enhancement
**Effort:** High | **Value:** High | **Priority Score:** 1.0

#### Problem Statement

The roadmap lists "MCP server for tool exposure" as a key feature, but no implementation exists. An MCP server would allow AutoRCA-Core to be used directly from Claude Desktop, Claude Code, and other MCP-compatible clients, dramatically increasing accessibility and integration potential.

#### Proposed Solution

1. Create an MCP server module at `autorca_core/mcp/server.py`
2. Expose key tools:
   - `run_rca` - Execute RCA on provided data
   - `analyze_logs` - Analyze logs for anomalies
   - `get_service_graph` - Return service topology
   - `find_root_cause` - Find root cause candidates
3. Add CLI command: `autorca mcp-server`
4. Document integration with Claude Desktop

```python
# autorca_core/mcp/server.py
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("autorca-core")

@server.tool()
async def run_rca(
    logs_path: str,
    symptom: str,
    metrics_path: str | None = None,
    traces_path: str | None = None,
) -> str:
    """
    Run root cause analysis on observability data.

    Args:
        logs_path: Path to log files
        symptom: Description of the incident symptom
        metrics_path: Optional path to metrics
        traces_path: Optional path to traces

    Returns:
        Markdown-formatted RCA report
    """
    result = run_rca_from_files(
        logs_path=logs_path,
        metrics_path=metrics_path,
        traces_path=traces_path,
        primary_symptom=symptom,
    )
    return generate_markdown_report(result)

@server.tool()
async def analyze_service_graph(logs_path: str) -> dict:
    """Analyze logs and return service dependency graph."""
    logs = load_logs(logs_path)
    graph = build_service_graph(logs=logs)
    return graph.to_dict()
```

**Claude Desktop Configuration:**
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

#### Success Metrics
- MCP server starts and responds to tool calls
- Integration with Claude Desktop works end-to-end
- All 4 key tools are exposed and documented
- Error handling provides useful feedback to AI clients

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1)
- [ ] Feature #1: Fix File Glob Pattern Bug
- [ ] Feature #2: Replace print() with Structured Logging
- [ ] Feature #7: Add CI/CD Pipeline

### Phase 2: Core Functionality (Week 2)
- [ ] Feature #4: Add Configurable Detection Thresholds
- [ ] Feature #5: Add Input Validation and Size Limits

### Phase 3: Enhanced Features (Weeks 3-4)
- [ ] Feature #3: Implement Anthropic Claude LLM Integration
- [ ] Feature #6: Implement Interactive HTML Reports

### Phase 4: Platform Integration (Week 5)
- [ ] Feature #8: Create MCP Server Implementation

---

## Competing/Alternative Projects Comparison

| Feature | AutoRCA-Core | Loguru | OpenTelemetry Collector | Datadog RCA |
|---------|--------------|--------|------------------------|-------------|
| Graph-based analysis | Yes | No | No | Yes |
| Offline mode | Yes | N/A | Yes | No |
| LLM integration | Partial | No | No | Yes |
| Multi-signal correlation | Yes | No | Yes | Yes |
| Self-hosted | Yes | N/A | Yes | No |
| Open source | Yes | Yes | Yes | No |

**Key differentiators for AutoRCA-Core:**
- Designed for autonomous agent integration
- Lightweight with minimal dependencies
- Extensible rule-based reasoning
- Part of broader autonomous ops ecosystem

---

## Appendix: Identified Issues Summary

### Critical (Must Fix)
1. File glob patterns don't work in Python (`logs.py:45`, `metrics.py:47`, `traces.py:46`)

### High Priority
2. No input validation for file paths (security risk)
3. LLM integrations are non-functional stubs
4. `print()` statements instead of logging (27 occurrences)

### Medium Priority
5. Hardcoded detection thresholds
6. HTML reports are non-interactive
7. No CI/CD pipeline
8. Deprecated `datetime.utcnow()` usage

### Low Priority
9. CONTRIBUTING.md referenced but doesn't exist
10. No API documentation beyond docstrings
11. Limited test coverage

---

*Analysis completed by automated code review. Report generated for AutoRCA-Core v0.2.0.*
