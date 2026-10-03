# AutoRCA-Core (ADAPT-RCA)

> **Agentic Root Cause Analysis engine for AI-powered autonomous reliability, SRE, and support.**

AutoRCA-Core is a graph-based RCA engine that analyzes logs, metrics, traces, configs, and documentation to automatically identify root causes and recommend remediation steps. It's designed as a **reference architecture** for building autonomous operations and reliability agents.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## What This Is

AutoRCA-Core provides:

- **Multi-signal ingestion**: Logs, metrics, distributed traces, and config changes
- **Graph-based topology**: Builds service dependency graphs and causal relationships
- **Rule-based reasoning**: Deterministic heuristics for identifying root causes
- **LLM integration (optional)**: Enhance analysis with natural language insights
- **Autonomous-first design**: Built to be called by AI agents, UIs, and automation workflows

**Key differentiators:**
- Graph-based causal analysis over temporal event correlation
- Works offline with rules-only mode (no LLM required)
- Designed for integration into larger autonomous ops stacks

---

## Who This Is For

- **SRE teams** investigating production incidents
- **DevOps engineers** correlating failures across services
- **Platform teams** building autonomous reliability agents
- **Architects** designing AI-powered troubleshooting workflows

AutoRCA-Core is part of a broader **autonomous operations ecosystem** including:
- [`awesome-autonomous-ops`](https://github.com/nik-kale/awesome-autonomous-ops) – Curated list of AI ops tools
- [`Secure-MCP-Gateway`](https://github.com/nik-kale/Secure-MCP-Gateway) – Security-first MCP gateway for ops tools
- [`Ops-Agent-Desktop`](https://github.com/nik-kale/Ops-Agent-Desktop) – Visual mission control for autonomous ops agents
- `ADAPT-Agents` – Agent orchestration layer (companion repo)

---

## Architecture Overview

AutoRCA-Core follows a **layered architecture** for clarity and extensibility:

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI / API Layer                        │
│            (autorca CLI, Python API, MCP server)            │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                     Reasoning Layer                         │
│   ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │
│   │   Rules    │  │  LLM (opt) │  │  Reasoning Loop  │    │
│   │ Heuristics │  │ Interface  │  │  Orchestration   │    │
│   └────────────┘  └────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    Graph Engine Layer                       │
│   ┌─────────────────────┐  ┌─────────────────────────┐    │
│   │   Graph Builder     │  │   Graph Queries         │    │
│   │ (topology + events) │  │ (causal chains, RCA)    │    │
│   └─────────────────────┘  └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    Ingestion Layer                          │
│   ┌──────┐  ┌─────────┐  ┌────────┐  ┌─────────────┐     │
│   │ Logs │  │ Metrics │  │ Traces │  │ Configs     │     │
│   └──────┘  └─────────┘  └────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                Data Sources (files, APIs, streams)          │
└─────────────────────────────────────────────────────────────┘
```

**Key concepts:**
- **Service Graph**: Topology of services and dependencies inferred from traces
- **Incident Nodes**: Anomalies detected (error spikes, latency, resource exhaustion)
- **Causal Chains**: Dependency paths showing how failures propagate
- **Root Cause Candidates**: Ranked list with confidence scores and evidence

---

## Quickstart

### Prerequisites
- Python 3.10+
- (Optional) Anthropic API key for LLM-enhanced summaries

### Installation

```bash
# Clone the repository
git clone https://github.com/nik-kale/AutoRCA-Core.git
cd AutoRCA-Core

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Or install with LLM support
pip install -e ".[llm]"
```

### Run the Quickstart Example

```bash
autorca quickstart
```

This runs RCA on synthetic logs and metrics simulating a **database connection pool exhaustion incident**. You'll see:
- Top root cause: resource exhaustion in `postgres`
- Error and latency spikes in `user-service` and `api-gateway`, ranked below it
- Remediation steps for each candidate, and an incident timeline

The quickstart data has no traces, so no dependency edges or causal chains are
inferred; run `autorca run ... --traces <spans>` on data with spans to get them.

### Run on Your Own Data

```bash
autorca run \
  --logs /path/to/logs \
  --metrics /path/to/metrics \
  --symptom "Checkout API returning 500 errors" \
  --output report.md
```

Use `--format json` or `--format html` for other report formats; without
`--output` the report is written to stdout and progress messages to stderr.
`--from`/`--to` restrict the analysis to a time window (ISO 8601; timestamps
without an offset are treated as UTC).

**Supported formats:**
- Logs: JSON Lines, plain text (auto-parsed)
- Metrics: CSV, JSON Lines, JSON arrays
- Traces: JSON / JSON Lines records with one span per object, using
  snake_case or camelCase field names (`trace_id`/`traceId`,
  `span_id`/`spanId`, `parent_span_id`/`parentSpanId`, `start_time`/`startTime`).
  OTLP `resourceSpans` exports and Jaeger UI `{"data": [...]}` exports must be
  flattened first.
- Configs: JSON, JSON Lines, YAML (deployment/config change events)

Directory sources are read recursively. Ingestion enforces `IngestionLimits`
(file size, files per directory, total events); pass `limits=` to the `load_*`
functions to change them.

---

## Usage as a Library

```python
from datetime import datetime
from autorca_core import run_rca, DataSourcesConfig, AnthropicLLM

# Define the incident time window (naive datetimes are treated as UTC)
window = (
    datetime(2025, 11, 10, 10, 0, 0),
    datetime(2025, 11, 10, 10, 5, 0),
)

# Configure data sources
sources = DataSourcesConfig(
    logs_dir="./logs",
    metrics_dir="./metrics",
    traces_dir="./traces",
)

# Run RCA
result = run_rca(
    incident_window=window,
    primary_symptom="API 500 errors",
    data_sources=sources,
)

# Access results
print(f"Top root cause: {result.root_cause_candidates[0].service}")
print(f"Confidence: {result.root_cause_candidates[0].confidence:.0%}")
print(result.summary)
```

### With LLM Enhancement (Anthropic Claude)

```python
import os
from autorca_core import run_rca, DataSourcesConfig, AnthropicLLM

# Initialize Anthropic LLM (requires `pip install -e ".[llm]"` and ANTHROPIC_API_KEY)
llm = AnthropicLLM(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    model="claude-sonnet-5-5",  # the default
)

# Run RCA with LLM enhancement
result = run_rca(
    incident_window=window,
    primary_symptom="API 500 errors",
    data_sources=sources,
    llm=llm,  # Add LLM for enhanced summaries
)

# Get comprehensive AI-generated analysis
print(result.summary)  # Structured RCA with executive summary, impact assessment, and remediation
# If the API call fails, summary falls back to the rule-based (DummyLLM) summary.

# Check token usage and costs
stats = llm.get_usage_stats()
print(f"Tokens used: {stats['total_tokens']}, Cost: ${stats['total_cost_usd']:.4f}")
```

---

## How This Fits an Autonomous Ops Stack

AutoRCA-Core is designed to be a **composable building block** in AI-powered operations workflows:

### Integration Patterns

1. **Agent-driven troubleshooting**
   - Autonomous agents (e.g., from `ADAPT-Agents`) call AutoRCA-Core to investigate incidents
   - RCA results guide next actions: gather more data, escalate, or remediate

2. **MCP exposure via Secure-MCP-Gateway**
   - Expose AutoRCA-Core as an MCP tool for Claude Desktop, Ops-Agent-Desktop, or other MCP clients
   - Enable AI assistants to perform RCA with policy controls and human-in-the-loop approvals

3. **Visual investigation in Ops-Agent-Desktop**
   - Ops-Agent-Desktop calls AutoRCA-Core and visualizes causal graphs in real-time
   - Shows live incident timelines and reasoning steps

4. **Runbook automation**
   - Use AutoRCA-Core to detect root causes, then trigger automated remediation via Ansible, Terraform, or K8s operators

---

## Project Structure

```
AutoRCA-Core/
├── autorca_core/              # Main package
│   ├── ingestion/             # Data loaders (logs, metrics, traces, configs)
│   ├── model/                 # Data models (events, graphs)
│   ├── graph_engine/          # Graph construction and querying
│   ├── reasoning/             # RCA logic (rules, LLM, loop)
│   ├── outputs/               # Report generation (markdown, JSON, HTML)
│   ├── mcp/                   # MCP server (see docs/MCP_INTEGRATION.md)
│   └── cli/                   # CLI interface
├── examples/                  # Example data and scenarios
│   └── quickstart_local_logs/ # Quickstart synthetic data
├── tests/                     # Test suite
├── docs/                      # Architecture and usage docs
├── pyproject.toml             # Package configuration
├── README.md                  # This file
└── LICENSE                    # MIT license
```

---

## Extending AutoRCA-Core

AutoRCA-Core is designed for extensibility:

### Add Custom Parsers
Implement custom log/metric parsers by extending ingestion modules:
```python
# autorca_core/ingestion/custom_parser.py
from autorca_core.model.events import LogEvent

def parse_custom_format(line: str) -> LogEvent:
    # Your parsing logic
    ...
```

### Add Custom Rules
Add domain-specific heuristics:
```python
# autorca_core/reasoning/custom_rules.py
from autorca_core.reasoning.rules import RootCauseCandidate

def rule_custom_pattern(graph):
    # Detect custom incident patterns
    ...
    return [RootCauseCandidate(...)]
```

### Integrate Custom LLMs
Implement the `LLMInterface` protocol:
```python
from autorca_core.reasoning.llm import LLMInterface

class MyCustomLLM:
    def summarize_rca(self, graph, candidates, symptom):
        # Call your LLM
        ...
```

---

## Roadmap

- [x] Core graph-based RCA engine
- [x] Multi-signal ingestion (logs, metrics, traces, configs)
- [x] Rule-based reasoning with causal chains
- [x] CLI and Python API
- [x] Anthropic LLM integration
- [ ] OpenAI LLM integration (`OpenAILLM` is a stub)
- [x] MCP server for tool exposure
- [ ] Prometheus and OpenTelemetry native connectors
- [x] Interactive HTML reports with graph visualizations
- [ ] Kubernetes and service mesh topology providers
- [ ] Pre-built RCA templates for common incident types (DB saturation, DNS, auth)

---

## Contributing

Contributions are welcome! This project aims to be a **reference architecture** for autonomous ops tools.

**How to contribute:**
- Open issues for bugs or feature requests
- Submit PRs for parsers, heuristics, or integrations
- Share anonymized incident examples for testing
- Suggest improvements to the reasoning engine

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Security and Safety

AutoRCA-Core performs **read-only analysis** by default. It does not execute commands or modify systems.

For production use:
- **Validate data sources**: Ensure logs/metrics are from trusted sources
- **Sanitize sensitive data**: Remove PII, secrets, and credentials before analysis
- **Use Secure-MCP-Gateway**: When exposing AutoRCA-Core as a tool, use policy controls and human approvals
- **Restrict MCP file access**: Set `AUTORCA_MCP_ALLOWED_ROOTS` so the MCP tools can only read the directories you list (see [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md))

Text taken from the analysed data (log messages, service names) is HTML-escaped in HTML reports.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

AutoRCA-Core draws inspiration from:
- Academic research in fault localization and causal inference
- Production RCA workflows at large-scale SaaS and cloud providers
- The growing ecosystem of AI-powered operations tools

**Built by [Nik Kale](https://github.com/nik-kale)** as part of an open-source initiative to advance autonomous operations and reliability engineering.

---

## Support

If you find AutoRCA-Core useful:
- ⭐ **Star the repo** to help others discover it
- 📢 **Share it** with your SRE, DevOps, and platform teams
- 🐛 **Open issues** with real-world scenarios (sanitized) to help improve the engine
- 🤝 **Contribute** parsers, rules, or integrations

For questions and discussions, open a [GitHub issue](https://github.com/nik-kale/AutoRCA-Core/issues).

---

**AutoRCA-Core**: Foundation for autonomous reliability agents. Graph-based RCA over logs, metrics, and traces.
