# ADAPT-RCA Examples

## Basic Usage

### Example 1: Analyzing Sample Logs

```bash
python -m adapt_rca.cli \
  --input examples/basic_logs/sample_logs.jsonl \
  --output results.json
```

This will analyze the sample logs and output:
- Human-readable incident summary to console
- Machine-readable JSON to `results.json`

### Example 2: Custom Log Analysis

Create your own log file in JSONL format:

```json
{"timestamp": "2025-11-16T14:00:00Z", "service": "auth-service", "level": "ERROR", "message": "Failed login attempt from IP 192.168.1.100"}
{"timestamp": "2025-11-16T14:00:05Z", "service": "auth-service", "level": "ERROR", "message": "Failed login attempt from IP 192.168.1.100"}
{"timestamp": "2025-11-16T14:00:10Z", "service": "auth-service", "level": "WARN", "message": "Account locked for user john@example.com"}
```

Then run:

```bash
python -m adapt_rca.cli --input my_logs.jsonl
```

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
