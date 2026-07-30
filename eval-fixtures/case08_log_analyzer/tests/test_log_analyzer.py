import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from log_analyzer import analyze_logs


class LogAnalyzerTests(unittest.TestCase):

    def test_basic_parsing_and_metrics(self):
        log = (
            "[2024-01-15 10:30:45] INFO  [auth] user=alice action=login ip=192.168.1.1 duration_ms=120\n"
            "[2024-01-15 10:31:02] ERROR [db]   user=bob action=query sql=SELECT+*+FROM+users error=timeout duration_ms=5000\n"
            "[2024-01-15 10:31:15] WARN  [api]  endpoint=/users method=GET status=503 duration_ms=3200\n"
            "[2024-01-15 10:32:00] INFO  [auth] user=charlie action=logout ip=10.0.0.1 duration_ms=45\n"
        )
        result = analyze_logs(log)
        self.assertIn("metrics", result)
        self.assertIn("anomalies", result)
        self.assertIn("auth", result["metrics"])
        self.assertIn("db", result["metrics"])
        self.assertIn("api", result["metrics"])
        self.assertEqual(result["metrics"]["auth"]["total_requests"], 2)
        self.assertEqual(result["metrics"]["db"]["errors"], 1)
        self.assertEqual(result["metrics"]["api"]["errors"], 0)

    def test_empty_log(self):
        result = analyze_logs("")
        self.assertEqual(result, {"metrics": {}, "anomalies": []})

    def test_malformed_lines_are_skipped(self):
        log = (
            "garbage line here\n"
            "[2024-01-15 10:30:45] INFO  [test] key=val duration_ms=100\n"
            "no timestamp or duration\n"
            "[2024-01-15 10:31:00] WARN  [test] key=val\n"
        )
        result = analyze_logs(log)
        self.assertIn("test", result["metrics"])
        self.assertEqual(result["metrics"]["test"]["total_requests"], 1)

    def test_duration_stats(self):
        log = (
            "[2024-01-15 10:00:00] INFO  [svc] x=1 duration_ms=100\n"
            "[2024-01-15 10:00:01] INFO  [svc] x=2 duration_ms=200\n"
            "[2024-01-15 10:00:02] INFO  [svc] x=3 duration_ms=300\n"
            "[2024-01-15 10:00:03] INFO  [svc] x=4 duration_ms=400\n"
            "[2024-01-15 10:00:04] INFO  [svc] x=5 duration_ms=500\n"
        )
        result = analyze_logs(log)
        d = result["metrics"]["svc"]["duration"]
        self.assertEqual(d["min"], 100)
        self.assertEqual(d["max"], 500)
        self.assertEqual(d["avg"], 300.0)
        self.assertEqual(d["median"], 300.0)
        self.assertAlmostEqual(d["p95"], 500.0, delta=1)

    def test_anomaly_duration_spike(self):
        log = (
            "[2024-01-15 10:00:00] INFO  [spike] x=1 duration_ms=100\n"
            "[2024-01-15 10:00:01] INFO  [spike] x=2 duration_ms=150\n"
            "[2024-01-15 10:00:02] INFO  [spike] x=3 duration_ms=120\n"
            "[2024-01-15 10:00:03] INFO  [spike] x=4 duration_ms=200\n"
            "[2024-01-15 10:00:04] INFO  [spike] x=5 duration_ms=10000\n"
        )
        result = analyze_logs(log)
        anomalies = result["anomalies"]
        spike_anomalies = [a for a in anomalies if a["type"] == "duration_spike"]
        self.assertGreaterEqual(len(spike_anomalies), 1)
        self.assertEqual(spike_anomalies[0]["service"], "spike")

    def test_anomaly_fatal_error(self):
        log = (
            "[2024-01-15 10:00:00] FATAL [critical] msg=boom duration_ms=50\n"
        )
        result = analyze_logs(log)
        fatalities = [a for a in result["anomalies"] if a["type"] == "fatal_error"]
        self.assertEqual(len(fatalities), 1)
        self.assertEqual(fatalities[0]["service"], "critical")

    def test_anomaly_rate_anomaly(self):
        lines = []
        for i in range(12):
            ts = f"2024-01-15 10:00:{i:02d}"
            lines.append(f"[{ts}] ERROR [flood] req={i} duration_ms=100")
        log = "\n".join(lines)
        result = analyze_logs(log)
        rate_anomalies = [a for a in result["anomalies"] if a["type"] == "rate_anomaly"]
        self.assertGreaterEqual(len(rate_anomalies), 1)

    def test_single_line_log(self):
        log = "[2024-01-15 10:00:00] INFO  [lonely] x=y duration_ms=42\n"
        result = analyze_logs(log)
        self.assertIn("lonely", result["metrics"])
        self.assertEqual(result["metrics"]["lonely"]["total_requests"], 1)
        d = result["metrics"]["lonely"]["duration"]
        self.assertEqual(d["min"], 42)
        self.assertEqual(d["max"], 42)
        self.assertEqual(d["avg"], 42.0)

    def test_error_pct_calculation(self):
        log = (
            "[2024-01-15 10:00:00] INFO  [svc] x=1 duration_ms=100\n"
            "[2024-01-15 10:00:01] ERROR [svc] x=2 duration_ms=100\n"
            "[2024-01-15 10:00:02] INFO  [svc] x=3 duration_ms=100\n"
            "[2024-01-15 10:00:03] FATAL [svc] x=4 duration_ms=100\n"
        )
        result = analyze_logs(log)
        self.assertEqual(result["metrics"]["svc"]["errors"], 2)
        self.assertEqual(result["metrics"]["svc"]["error_pct"], 50.0)

    def test_no_spike_detection_for_single_point(self):
        log = "[2024-01-15 10:00:00] INFO  [single] x=1 duration_ms=9999\n"
        result = analyze_logs(log)
        spikes = [a for a in result["anomalies"] if a["type"] == "duration_spike"]
        self.assertEqual(len(spikes), 0)

    def test_line_numbers_are_correct(self):
        log = (
            "bad line\n"
            "[2024-01-15 10:00:01] FATAL [test] x=1 duration_ms=100\n"
        )
        result = analyze_logs(log)
        anomalies = result["anomalies"]
        self.assertEqual(anomalies[0]["line_number"], 2)


if __name__ == "__main__":
    unittest.main()
