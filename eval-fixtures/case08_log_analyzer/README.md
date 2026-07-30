# Case 08: Structured Log Parser & Anomaly Detector (Multi-Library)

Implement `log_analyzer.py` so that the test suite passes.

**Note:** This requires using `re`, `datetime`, `collections`, `statistics`, and `json` from the Python standard library. You may also use `math`.

## Log Format

Each line in a log file follows this structure:

```
[YYYY-MM-DD HH:MM:SS] LEVEL  [service] key1=value1 key2=value2 ... duration_ms=N
```

Where:
- `LEVEL` is one of: `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`
- `service` is a lowercase identifier (`[auth]`, `[db]`, `[api]`, `[worker]`, `[cache]`)
- key=value pairs are space-separated, values are unquoted non-whitespace strings
- `duration_ms` is always present in every line (positive integer)
- Lines may be separated by `\n` or `\r\n`

Example:
```
[2024-01-15 10:30:45] INFO  [auth] user=alice action=login ip=192.168.1.1 duration_ms=120
[2024-01-15 10:31:02] ERROR [db]   user=bob action=query sql=SELECT+*+FROM+users error=timeout duration_ms=5000
[2024-01-15 10:31:15] WARN  [api]  endpoint=/users method=GET status=503 duration_ms=3200
[2024-01-15 10:32:00] INFO  [auth] user=charlie action=logout ip=10.0.0.1 duration_ms=45
```

## Requirements

Export a function `analyze_logs(log_text: str) -> dict` that returns a dict with two keys:

### `metrics` — dict keyed by service name
Each value is a dict:
```python
{
    "total_requests": int,      # total lines for this service
    "errors": int,              # lines with ERROR or FATAL level
    "error_pct": float,         # errors / total * 100, rounded to 2 decimal places
    "duration": {               # duration stats in milliseconds
        "min": int,
        "max": int,
        "avg": float,           # rounded to 1 decimal place
        "median": float,        # median of all durations, rounded to 1 decimal place
        "p95": float            # 95th percentile, rounded to 1 decimal place
    },
    "active_hours": float       # hours between first and last timestamp for this service, rounded to 2
}
```

### `anomalies` — list of dicts
An anomaly is any line where ANY of these conditions hold:
1. **Duration spike**: duration `> (service_mean + 3 * service_stddev)` AND duration `>= 2000`
2. **Fatal error**: LEVEL is `FATAL` (regardless of duration)
3. **Rate anomaly**: more than 10 ERROR/FATAL lines for the same service within any 60-second window

Each anomaly dict:
```python
{
    "line_number": int,         # 1-indexed line in the raw log
    "type": str,                # "duration_spike" | "fatal_error" | "rate_anomaly"
    "service": str,
    "timestamp": str,           # ISO format: "2024-01-15T10:30:45"
    "detail": str               # Human-readable description
}
```

### Edge cases to handle:
- **Malformed lines**: lines that don't match the format are skipped (not counted in any metric). Extract as many fields as possible before declaring malformed. A line with a valid timestamp but missing `duration_ms` is considered malformed.
- **Empty log**: return `{"metrics": {}, "anomalies": []}`
- **Single service only**: still compute stats normally
- **All ERROR**: p95, median should still be valid
- **statistics.StdevError**: if a service has fewer than 2 data points, use `0.0` for stddev (skip spike detection for that service)

## Constraints

- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `log_analyzer.py`.
