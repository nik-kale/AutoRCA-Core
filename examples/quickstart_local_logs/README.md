# Quickstart Example

This directory contains synthetic example data for demonstrating AutoRCA-Core.

## Scenario

This example simulates a database connection pool exhaustion incident:

1. **Root Cause:** PostgreSQL database reaches max connections (200/200)
2. **Propagation:**
   - User service cannot acquire DB connections
   - API gateway experiences upstream timeouts
   - Frontend sees 500 errors
3. **Timeline:** Incident occurs over ~2 minutes

## Files

- `logs.jsonl` - Synthetic log events showing the error cascade
- `metrics.jsonl` - Metrics showing connection pool saturation and latency spikes
- `README.md` - This file

## Running the Example

```bash
# From the repository root
autorca quickstart

# Or manually specify the data
autorca run \
  --logs examples/quickstart_local_logs/logs.jsonl \
  --metrics examples/quickstart_local_logs/metrics.jsonl \
  --symptom "Database connection exhaustion causing API errors"
```

## Expected Output

AutoRCA-Core should identify:
- **Root Cause:** resource exhaustion in `postgres` (85% confidence), from the
  `cpu_percent` samples above 90%
- **Other candidates:** error spikes in `user-service` and `api-gateway`
- **Remediation:** scale `postgres` resources and check for connection leaks or
  inefficient queries

This directory has no trace data, so the service graph has no dependency edges
and no causal chain is reported. With spans linking the services, AutoRCA-Core
infers dependencies and reports a propagation chain such as
`postgres → user-service → api-gateway → frontend`.

Only CPU and memory metrics are checked for resource exhaustion today, so the
`connections_active` series is loaded but not flagged on its own.
