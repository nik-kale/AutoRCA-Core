# ADAPT-RCA Architecture

## Overview

ADAPT-RCA is designed as a modular, extensible system for analyzing logs and events to identify root causes of incidents.

## Components

### 1. Ingestion Layer
- **Purpose**: Load and parse raw log data from various sources
- **Current Implementation**: JSONL file loader
- **Future Extensions**:
  - API endpoints for real-time ingestion
  - Connectors for observability platforms (Prometheus, Datadog, etc.)
  - S3/cloud storage integrations

### 2. Parsing & Normalization
- **Purpose**: Transform diverse log formats into a unified event schema
- **Current Implementation**: Simple field mapping
- **Future Extensions**:
  - Pattern-based parsing for unstructured logs
  - Field extraction with regex/grok patterns
  - Schema validation

### 3. Reasoning Engine
- **Purpose**: Analyze events to identify patterns and propose root causes
- **Current Implementation**: Basic grouping heuristics
- **Future Extensions**:
  - LLM-powered causal inference
  - Statistical anomaly detection
  - Time-series correlation
  - Multi-agent reasoning loops

### 4. Causal Graph Builder
- **Purpose**: Model dependencies and relationships between components
- **Current Implementation**: Simple graph structure
- **Future Extensions**:
  - Topology discovery (Kubernetes, service mesh)
  - Dependency tracking from deployment metadata
  - Graph visualization

### 5. Reporting & Output
- **Purpose**: Present findings in human and machine-readable formats
- **Current Implementation**: CLI text output, JSON export
- **Future Extensions**:
  - HTML/Markdown incident reports
  - Dashboard UI
  - Integration with ticketing systems (Jira, PagerDuty)

## Configuration

ADAPT-RCA is configured via environment variables:

- `ADAPT_RCA_LLM_PROVIDER`: LLM provider (e.g., "openai", "local")
- `ADAPT_RCA_LLM_MODEL`: Model identifier
- `ADAPT_RCA_MAX_EVENTS`: Maximum events to process
- `ADAPT_RCA_TIME_WINDOW`: Time window for event grouping (minutes)

## Extensibility Points

1. **Custom Parsers**: Add new parsers in `src/adapt_rca/parsing/`
2. **Custom Heuristics**: Add reasoning rules in `src/adapt_rca/reasoning/heuristics.py`
3. **Custom Exporters**: Add output formats in `src/adapt_rca/reporting/exporters.py`
4. **Custom Ingestors**: Add data sources in `src/adapt_rca/ingestion/`
