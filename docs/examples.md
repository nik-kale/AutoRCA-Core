# AutoRCA-Core Examples

## Basic Usage

### Example 1: Analyzing the Quickstart Data

```bash
autorca run \
  --logs examples/quickstart_local_logs/logs.jsonl \
  --metrics examples/quickstart_local_logs/metrics.jsonl \
  --symptom "Checkout API returning 500 errors" \
  --format json \
  --output results.json
```

This writes the machine-readable RCA report to `results.json`; progress messages
go to stderr. Omit `--output` to print the report to stdout, and use
`--format markdown` (the default) or `--format html` for the other formats.

### Example 2: Custom Log Analysis

Create your own log file in JSONL format (see `examples/basic_logs/sample_logs.jsonl`
for a minimal sample):

```json
{"timestamp": "2025-11-16T14:00:00Z", "service": "auth-service", "level": "ERROR", "message": "Failed login attempt from IP 192.168.1.100"}
{"timestamp": "2025-11-16T14:00:05Z", "service": "auth-service", "level": "ERROR", "message": "Failed login attempt from IP 192.168.1.100"}
{"timestamp": "2025-11-16T14:00:10Z", "service": "auth-service", "level": "WARN", "message": "Account locked for user john@example.com"}
```

Then run:

```bash
autorca run --logs my_logs.jsonl --symptom "Repeated failed logins"
```

By default an error spike needs 3 errors from one service within 5 minutes. From
Python, pass a `ThresholdConfig` (for example `ThresholdConfig.strict()` or
`ThresholdConfig.from_env()`) to `run_rca(..., thresholds=...)` to tune detection;
see [architecture.md](architecture.md).

## Use Cases

### SaaS Outage Analysis

**Scenario**: API gateway experiencing high latency and errors after a deployment.

**Log Data**:
- API gateway logs showing timeouts
- Backend service logs showing database connection issues
- Database logs showing connection pool exhaustion

**Expected Output**:
- Root cause: Database connection pool misconfiguration
- Recommended action: Increase connection pool size or implement connection pooling at application layer

### Security Incident Triage

**Scenario**: Multiple failed login attempts followed by account lockouts.

**Log Data**:
- Authentication service logs
- Firewall logs
- Endpoint security logs

**Expected Output**:
- Root cause: Credential stuffing attack from specific IP range
- Recommended action: Block IP range, enable rate limiting, notify affected users

### Release Validation

**Scenario**: Comparing logs before and after a deployment to identify regressions.

**Approach**:
1. Analyze logs from before deployment
2. Analyze logs from after deployment
3. Compare results to identify new errors or patterns

## Future Examples

- Kubernetes pod crash analysis
- Microservices dependency failure
- Database query performance degradation
- CDN/edge cache issues
- DNS resolution failures
