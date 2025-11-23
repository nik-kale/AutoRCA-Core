# ADAPT-RCA

**ADAPT-RCA (Adaptive Diagnostic Agent for Proactive Troubleshooting – Root Cause Analyzer)** is an open-source agentic AI engine that analyzes logs, events, and telemetry to identify likely root causes and recommend remediation steps.

It is designed for **cloud**, **SaaS**, and **security** environments where teams are flooded with signals but lack time to manually correlate everything.

---

## 🔍 What ADAPT-RCA Does

- Ingests **logs, alerts, and events** from your systems (JSON, text, CSV).
- Uses an **agentic AI reasoning loop** to:
  - Cluster related events
  - Identify anomalies / breakpoints
  - Propose **probable root causes**
  - Suggest **next-step actions** (e.g., restart service, roll back deploy, update config).
- Produces:
  - A **human-readable incident summary**
  - A **graph of suspected dependencies / causal links** (e.g., service → DB → config)
  - Optional **machine-readable JSON output** for downstream automation.

ADAPT-RCA is meant to be:
- **Extensible** – plug in your own parsers, log schemas, and tools.
- **Composable** – run as a CLI, library, or part of your existing pipeline.
- **Transparent** – every reasoning step is logged and inspectable.

---

## 🧠 Architecture Overview

At a high level, ADAPT-RCA consists of:

1. **Ingestion Layer**
   - Connectors for log files (local), JSON events, and simple HTTP inputs.
   - Normalizes records into a common event model.

2. **Enrichment & Parsing**
   - Extracts key fields (service, timestamp, severity, error codes, request IDs, etc.).
   - Optional enrichment with deployment metadata or topology.

3. **Agentic Reasoning Engine**
   - Analyzes patterns, time windows, and relationships.
   - Uses an LLM (local or hosted) to:
     - Group related events into candidate incidents.
     - Hypothesize root causes.
     - Propose mitigation actions.

4. **Causal Graph Builder**
   - Builds a directed graph of components, errors, and dependencies.
   - Annotates edges with evidence (log lines, metrics, time deltas).

5. **Report & Output**
   - CLI output for humans.
   - JSON/YAML output for automation.
   - Optional HTML/Markdown incident report.

---

## ✨ Example Use Cases

- **SaaS outage analysis**: You upload API gateway logs + DB errors → ADAPT-RCA suggests that a misconfigured rollout to `v2` of a service caused a surge in 500s.
- **Security incident triage**: You feed in auth logs, firewall alerts, and endpoint events → ADAPT-RCA correlates them into a single suspected credential abuse incident.
- **Release validation**: Compare logs from "before" and "after" a deployment to see what changed and where breakages are likely.

---

## 🚀 Getting Started

> **Prerequisites**
> - Python 3.10+
> - Access to an LLM endpoint (OpenAI, Gemini, local model, etc.) – optional for basic rule-based mode.

```bash
# Clone the repo
git clone https://github.com/<your-username>/ADAPT-RCA.git
cd ADAPT-RCA

# (Optional) Create and activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Quickstart Example

### 1. Prepare sample logs

Create a file `sample_logs.jsonl`:

```json
{"timestamp": "2025-11-10T10:00:00Z", "service": "api-gateway", "level": "ERROR", "message": "Upstream timeout calling user-service"}
{"timestamp": "2025-11-10T10:00:03Z", "service": "user-service", "level": "ERROR", "message": "DB connection pool exhausted"}
{"timestamp": "2025-11-10T10:00:05Z", "service": "postgres", "level": "WARN", "message": "Max connections reached"}
```

### 2. Run ADAPT-RCA in CLI mode

```bash
python -m adapt_rca.cli \
  --input examples/basic_logs/sample_logs.jsonl \
  --output results.json
```

### 3. Example output (simplified)

```json
{
  "incident_summary": "API latency and errors caused by exhausted DB connections.",
  "probable_root_causes": [
    "Connection pool misconfiguration for user-service",
    "Sudden traffic spike without autoscaling"
  ],
  "recommended_actions": [
    "Increase max DB connections or enable connection pooling at app layer",
    "Enable autoscaling for user-service based on queue depth"
  ]
}
```

---

## 🧩 Project Structure

```
ADAPT-RCA/
  src/
    adapt_rca/
      __init__.py
      config.py
      cli.py
      ingestion/
        __init__.py
        file_loader.py
      parsing/
        __init__.py
        log_parser.py
      reasoning/
        __init__.py
        agent.py
        heuristics.py
      graph/
        __init__.py
        causal_graph.py
      reporting/
        __init__.py
        formatter.py
        exporters.py
  examples/
    basic_logs/
      sample_logs.jsonl
  docs/
    architecture.md
    examples.md
  tests/
    test_parsing.py
    test_reasoning.py
  requirements.txt
  README.md
  LICENSE
```

---

## 🛠 Configuration

You can configure ADAPT-RCA using environment variables or a config file:
- `ADAPT_RCA_LLM_PROVIDER` – e.g., openai, local
- `ADAPT_RCA_LLM_MODEL` – e.g., gpt-4.1-mini, gemini-1.5-pro
- `ADAPT_RCA_MAX_EVENTS` – limit on events per run
- `ADAPT_RCA_TIME_WINDOW` – time window (in minutes) to group events

See [docs/architecture.md](docs/architecture.md) for more details.

---

## 🔌 Extensibility

You can extend ADAPT-RCA by:
- Adding new parsers under `src/adapt_rca/parsing/`
- Adding new heuristics under `src/adapt_rca/reasoning/heuristics.py`
- Adding new exporters under `src/adapt_rca/reporting/exporters.py`
- Plugging into your own observability stack (e.g., shipping JSON into the ingestion layer)

Contributions are welcome – see CONTRIBUTING.md.

---

## 🧭 Roadmap (High-Level)
- Web dashboard for visualizing causal graphs
- Native integration with Prometheus / OpenTelemetry
- Pluggable topology provider (Kubernetes, service mesh, etc.)
- Templates for common incident types (DB saturation, DNS issues, auth failures)
- Examples for security-focused logs

---

## 📄 License

MIT License

---

## 🙌 Contributing

Issues, feature requests, and pull requests are welcome.

If you use ADAPT-RCA in your organisation, consider:
- Opening an issue describing your use case
- Contributing additional parsers or heuristics
- Sharing anonymized incident examples

---

## ⭐ Support

If you find ADAPT-RCA useful, consider:
- Starring the repo ⭐
- Sharing it with your SRE, DevOps, or Security teams
- Opening issues with real-world logs (sanitized) to help improve the engine
