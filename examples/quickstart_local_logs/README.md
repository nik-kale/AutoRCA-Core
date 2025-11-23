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
- **Root Cause:** PostgreSQL connection pool exhaustion (high confidence)
- **Evidence:** Max connections reached, connection pool errors
- **Remediation:** Increase DB connection pool size, check for connection leaks

The causal chain should show:
`postgres → user-service → api-gateway → frontend`
