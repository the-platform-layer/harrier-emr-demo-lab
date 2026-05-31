"""Tests for the Slice 19 scenario validation harness.

Covers harrier_client, compare, report, and validate modules without
making live HTTP or AWS calls.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.compare import ComparisonResult, ValidationCheck, compare
from validation.harrier_client import HarrierClient, HarrierClientError
from validation.report import format_report, print_summary, write_report
from validation.validate import (
    _RUNNING_SIGNAL_FIELDS,
    _fresh_context_file,
    _listing_has_log_file,
    build_mcp_request,
    load_json,
    normalize_s3_uri,
    parse_args,
    run_scenario,
    wait_for_emr_s3_logs,
    wait_for_eks_job,
    wait_for_serverless_job,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    body: bytes,
    content_type: str = "application/json",
    session_id: str = "",
    status: int = 200,
) -> MagicMock:
    """Return a mock object that mimics urllib.request.urlopen context manager."""
    resp = MagicMock()
    resp.read.return_value = body
    resp.headers = {
        "Content-Type": content_type,
        "Mcp-Session-Id": session_id,
    }
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _sse(events: list[dict]) -> bytes:
    """Build an SSE byte stream from a list of JSON-RPC envelopes."""
    lines = []
    for event in events:
        lines.append(f"data: {json.dumps(event)}")
        lines.append("")
    return ("\n".join(lines) + "\n").encode()


def _json_rpc_result(req_id: int, result: dict) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}).encode()


def _tool_content(payload: dict) -> dict:
    """Wrap a payload dict as an MCP tool result with a text content block."""
    return {
        "content": [{"type": "text", "text": json.dumps(payload)}],
        "isError": False,
    }


def _start_response(
    investigation_id: str = "inv-abc123",
    category: str = "EXECUTOR_OOM",
    rec_type: str = "SPARK_CONFIG",
    pr_ready: bool = True,
) -> dict:
    return {
        "investigation_id": investigation_id,
        "status": "completed",
        "root_cause": {
            "category": category,
            "summary": "test summary",
            "confidence": 0.9,
            "affected_component": "executor",
        },
        "recommendations": [
            {"type": rec_type, "title": "Adjust memory", "risk": "low", "pr_ready": pr_ready}
        ],
    }


# ---------------------------------------------------------------------------
# HarrierClient — SSE parsing
# ---------------------------------------------------------------------------


class TestParseSSE(unittest.TestCase):
    def _client(self) -> HarrierClient:
        return HarrierClient(mcp_url="http://localhost:8000/mcp")

    def test_finds_matching_id(self) -> None:
        client = self._client()
        notification = {"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}
        response = {"jsonrpc": "2.0", "id": 1, "result": {"answer": 42}}
        raw = _sse([notification, response])
        result = client._parse_sse(raw, req_id=1)
        self.assertEqual(result, {"answer": 42})

    def test_skips_non_matching_ids(self) -> None:
        client = self._client()
        events = [
            {"jsonrpc": "2.0", "id": 0, "result": {"other": True}},
            {"jsonrpc": "2.0", "id": 1, "result": {"mine": True}},
        ]
        raw = _sse(events)
        result = client._parse_sse(raw, req_id=1)
        self.assertEqual(result, {"mine": True})

    def test_returns_empty_when_no_match(self) -> None:
        client = self._client()
        raw = _sse([{"jsonrpc": "2.0", "id": 0, "result": {}}])
        result = client._parse_sse(raw, req_id=99)
        self.assertEqual(result, {})

    def test_returns_empty_for_blank_stream(self) -> None:
        client = self._client()
        self.assertEqual(client._parse_sse(b"", req_id=1), {})

    def test_raises_on_mcp_error_in_sse(self) -> None:
        client = self._client()
        raw = _sse([{"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "boom"}}])
        with self.assertRaises(HarrierClientError) as ctx:
            client._parse_sse(raw, req_id=1)
        self.assertIn("MCP error", str(ctx.exception))

    def test_skips_invalid_json_lines(self) -> None:
        client = self._client()
        raw = b"data: {bad json}\ndata: {\"id\": 1, \"result\": {\"ok\": true}}\n"
        result = client._parse_sse(raw, req_id=1)
        self.assertEqual(result, {"ok": True})

    def test_req_id_none_returns_any_result(self) -> None:
        client = self._client()
        raw = _sse([{"jsonrpc": "2.0", "id": 5, "result": {"hello": "world"}}])
        result = client._parse_sse(raw, req_id=None)
        self.assertEqual(result, {"hello": "world"})


# ---------------------------------------------------------------------------
# HarrierClient — content extraction
# ---------------------------------------------------------------------------


class TestExtractContent(unittest.TestCase):
    def _client(self) -> HarrierClient:
        return HarrierClient(mcp_url="http://localhost:8000/mcp")

    def test_parses_text_content_block(self) -> None:
        client = self._client()
        payload = {"investigation_id": "inv-1", "status": "completed"}
        rpc_result = _tool_content(payload)
        self.assertEqual(client._extract_content(rpc_result), payload)

    def test_returns_raw_on_non_json_text(self) -> None:
        client = self._client()
        rpc_result = {"content": [{"type": "text", "text": "not json"}]}
        result = client._extract_content(rpc_result)
        self.assertEqual(result, {"raw": "not json"})

    def test_falls_back_to_rpc_result_when_no_content(self) -> None:
        client = self._client()
        rpc_result = {"direct_key": "direct_value"}
        result = client._extract_content(rpc_result)
        self.assertEqual(result, {"direct_key": "direct_value"})

    def test_skips_non_text_content_blocks(self) -> None:
        client = self._client()
        rpc_result = {
            "content": [
                {"type": "image", "data": "base64..."},
                {"type": "text", "text": '{"found": true}'},
            ]
        }
        self.assertEqual(client._extract_content(rpc_result), {"found": True})


# ---------------------------------------------------------------------------
# HarrierClient — HTTP layer (mocked urlopen)
# ---------------------------------------------------------------------------


class TestHarrierClientHTTP(unittest.TestCase):
    def _client(self) -> HarrierClient:
        return HarrierClient(mcp_url="http://localhost:8000/mcp", timeout=5)

    @patch("urllib.request.urlopen")
    def test_call_tool_direct_json_response(self, mock_open) -> None:
        payload = _start_response()
        rpc = {"jsonrpc": "2.0", "id": 0, "result": _tool_content(payload)}
        mock_open.return_value = _make_response(_json_rpc_result(0, _tool_content(payload)))
        client = self._client()
        result = client.call_tool("harrier_start_emr_investigation", {"account_id": "123456789012"})
        self.assertEqual(result["investigation_id"], "inv-abc123")

    @patch("urllib.request.urlopen")
    def test_call_tool_sse_response(self, mock_open) -> None:
        payload = _start_response(investigation_id="inv-sse-001")
        sse_body = _sse([{"jsonrpc": "2.0", "id": 0, "result": _tool_content(payload)}])
        mock_open.return_value = _make_response(sse_body, content_type="text/event-stream")
        client = self._client()
        result = client.call_tool("harrier_start_emr_investigation", {})
        self.assertEqual(result["investigation_id"], "inv-sse-001")

    @patch("urllib.request.urlopen")
    def test_stores_session_id_from_header(self, mock_open) -> None:
        mock_open.return_value = _make_response(
            _json_rpc_result(0, {"protocolVersion": "2025-03-26", "capabilities": {}}),
            session_id="sess-xyz",
        )
        client = self._client()
        client.initialize()
        self.assertEqual(client._session_id, "sess-xyz")

    @patch("urllib.request.urlopen")
    def test_raises_harrier_client_error_on_http_error(self, mock_open) -> None:
        exc = urllib.error.HTTPError(
            url="http://localhost:8000/mcp",
            code=503,
            msg="Service Unavailable",
            hdrs=MagicMock(),
            fp=io.BytesIO(b"down"),
        )
        mock_open.side_effect = exc
        client = self._client()
        with self.assertRaises(HarrierClientError) as ctx:
            client.call_tool("harrier_start_emr_investigation", {})
        self.assertIn("503", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_raises_on_connection_refused(self, mock_open) -> None:
        mock_open.side_effect = OSError("Connection refused")
        client = self._client()
        with self.assertRaises(HarrierClientError):
            client.call_tool("harrier_start_emr_investigation", {})

    @patch("urllib.request.urlopen")
    def test_raises_on_mcp_error_in_direct_response(self, mock_open) -> None:
        error_body = json.dumps({
            "jsonrpc": "2.0",
            "id": 0,
            "error": {"code": -32600, "message": "Invalid Request"},
        }).encode()
        mock_open.return_value = _make_response(error_body)
        client = self._client()
        with self.assertRaises(HarrierClientError):
            client.call_tool("harrier_start_emr_investigation", {})

    @patch("urllib.request.urlopen")
    def test_empty_response_body_returns_empty_dict(self, mock_open) -> None:
        mock_open.return_value = _make_response(b"")
        client = self._client()
        result = client.call_tool("harrier_start_emr_investigation", {})
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# compare() — root cause checks
# ---------------------------------------------------------------------------


class TestCompareRootCause(unittest.TestCase):
    def test_exact_category_match_passes(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="EXECUTOR_OOM")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "root_cause_category")
        self.assertTrue(check.passed)
        self.assertEqual(result.outcome, "pass")

    def test_acceptable_related_category_passes(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "acceptable_related_categories": ["EXECUTOR_LOST"],
        }
        actual = _start_response(category="EXECUTOR_LOST")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "root_cause_category")
        self.assertTrue(check.passed)

    def test_wrong_category_fails(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="DRIVER_OOM")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "root_cause_category")
        self.assertFalse(check.passed)
        self.assertEqual(result.outcome, "fail")
        self.assertIn("DRIVER_OOM", check.message)

    def test_wrong_category_not_in_acceptable_fails(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "acceptable_related_categories": ["EXECUTOR_LOST"],
        }
        actual = _start_response(category="DATA_SKEW")
        result = compare(expected, actual)
        self.assertEqual(result.outcome, "fail")

    def test_happy_path_unknown_passes(self) -> None:
        expected = {"scenario": "happy_path", "expected_outcome": "success", "expected_findings": []}
        actual = _start_response(category="UNKNOWN")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "no_false_positive")
        self.assertTrue(check.passed)
        self.assertEqual(result.outcome, "pass")

    def test_happy_path_with_real_finding_fails(self) -> None:
        expected = {"scenario": "happy_path", "expected_outcome": "success", "expected_findings": []}
        actual = _start_response(category="EXECUTOR_OOM")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "no_false_positive")
        self.assertFalse(check.passed)
        self.assertEqual(result.outcome, "fail")


# ---------------------------------------------------------------------------
# compare() — recommendation type and pr_ready checks
# ---------------------------------------------------------------------------


class TestCompareRecommendations(unittest.TestCase):
    def test_recommendation_type_pass(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "recommendation_type": "SPARK_CONFIG",
        }
        actual = _start_response(category="EXECUTOR_OOM", rec_type="SPARK_CONFIG")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "recommendation_type")
        self.assertTrue(check.passed)

    def test_recommendation_type_fail(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "recommendation_type": "SPARK_CONFIG",
        }
        actual = _start_response(category="EXECUTOR_OOM", rec_type="RUNBOOK")
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "recommendation_type")
        self.assertFalse(check.passed)

    def test_pr_ready_true_passes_when_any_rec_is_ready(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "pr_ready": True,
        }
        actual = _start_response(category="EXECUTOR_OOM", pr_ready=True)
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "pr_ready")
        self.assertTrue(check.passed)

    def test_pr_ready_true_fails_when_no_rec_is_ready(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "pr_ready": True,
        }
        actual = _start_response(category="EXECUTOR_OOM", pr_ready=False)
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "pr_ready")
        self.assertFalse(check.passed)

    def test_pr_ready_false_passes_when_no_rec_is_ready(self) -> None:
        expected = {
            "scenario": "db_lock_timeout",
            "expected_root_cause_category": "DB_LOCK_TIMEOUT",
            "pr_ready": False,
        }
        actual = _start_response(category="DB_LOCK_TIMEOUT", rec_type="DB", pr_ready=False)
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "pr_ready")
        self.assertTrue(check.passed)

    def test_pr_ready_false_fails_when_rec_is_ready(self) -> None:
        expected = {
            "scenario": "db_lock_timeout",
            "expected_root_cause_category": "DB_LOCK_TIMEOUT",
            "pr_ready": False,
        }
        actual = _start_response(category="DB_LOCK_TIMEOUT", rec_type="DB", pr_ready=True)
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "pr_ready")
        self.assertFalse(check.passed)

    def test_optional_checks_skipped_when_absent_from_expected(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="EXECUTOR_OOM")
        result = compare(expected, actual)
        names = {c.name for c in result.checks}
        self.assertNotIn("recommendation_type", names)
        self.assertNotIn("pr_ready", names)


# ---------------------------------------------------------------------------
# compare() — result shape
# ---------------------------------------------------------------------------


class TestComparisonResultShape(unittest.TestCase):
    def test_outcome_is_fail_when_any_check_fails(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "recommendation_type": "SPARK_CONFIG",
        }
        # category matches but rec type does not
        actual = _start_response(category="EXECUTOR_OOM", rec_type="RUNBOOK")
        result = compare(expected, actual)
        self.assertEqual(result.outcome, "fail")

    def test_summary_contains_failed_check_names(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="DRIVER_OOM")
        result = compare(expected, actual)
        self.assertIn("root_cause_category", result.summary)
        self.assertIn("FAIL", result.summary)

    def test_root_cause_propagated_to_result(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="EXECUTOR_OOM")
        result = compare(expected, actual)
        self.assertEqual(result.root_cause["category"], "EXECUTOR_OOM")

    def test_recommendations_propagated_to_result(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = _start_response(category="EXECUTOR_OOM", rec_type="SPARK_CONFIG")
        result = compare(expected, actual)
        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0]["type"], "SPARK_CONFIG")

    def test_handles_missing_root_cause_gracefully(self) -> None:
        expected = {"scenario": "executor_oom", "expected_root_cause_category": "EXECUTOR_OOM"}
        actual = {}
        result = compare(expected, actual)
        self.assertEqual(result.outcome, "fail")

    def test_handles_empty_recommendations_list(self) -> None:
        expected = {
            "scenario": "executor_oom",
            "expected_root_cause_category": "EXECUTOR_OOM",
            "recommendation_type": "SPARK_CONFIG",
        }
        actual = {
            "investigation_id": "inv-1",
            "root_cause": {"category": "EXECUTOR_OOM", "summary": "", "confidence": 0.9},
            "recommendations": [],
        }
        result = compare(expected, actual)
        check = next(c for c in result.checks if c.name == "recommendation_type")
        self.assertFalse(check.passed)


# ---------------------------------------------------------------------------
# format_report and write_report
# ---------------------------------------------------------------------------


class TestReport(unittest.TestCase):
    def _make_result(self, outcome: str = "pass") -> ComparisonResult:
        check = ValidationCheck(
            name="root_cause_category",
            passed=(outcome == "pass"),
            expected="EXECUTOR_OOM",
            actual="EXECUTOR_OOM" if outcome == "pass" else "DRIVER_OOM",
            message="" if outcome == "pass" else "wrong category",
        )
        return ComparisonResult(
            scenario="executor_oom",
            investigation_id="inv-abc123",
            outcome=outcome,  # type: ignore[arg-type]
            checks=[check],
            root_cause={"category": "EXECUTOR_OOM"},
            recommendations=[{"type": "SPARK_CONFIG", "pr_ready": True}],
            summary="PASS: 1 check(s) passed" if outcome == "pass" else "FAIL: 1 of 1",
        )

    def test_format_report_has_required_keys(self) -> None:
        report = format_report(self._make_result("pass"))
        for key in ("scenario", "investigation_id", "outcome", "summary",
                    "validation_timestamp", "checks", "root_cause", "recommendations"):
            self.assertIn(key, report)

    def test_format_report_checks_are_dicts(self) -> None:
        report = format_report(self._make_result("pass"))
        self.assertIsInstance(report["checks"], list)
        self.assertIsInstance(report["checks"][0], dict)

    def test_format_report_timestamp_is_iso_string(self) -> None:
        report = format_report(self._make_result("pass"))
        ts = report["validation_timestamp"]
        self.assertIsInstance(ts, str)
        self.assertIn("T", ts)

    def test_write_report_creates_valid_json_file(self) -> None:
        result = self._make_result("pass")
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "report.json"
            write_report(result, output)
            self.assertTrue(output.is_file())
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["scenario"], "executor_oom")
            self.assertEqual(data["outcome"], "pass")

    def test_write_report_creates_parent_directories(self) -> None:
        result = self._make_result("fail")
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "sub" / "dir" / "report.json"
            write_report(result, output)
            self.assertTrue(output.is_file())

    def test_print_summary_outputs_scenario_name(self) -> None:
        result = self._make_result("pass")
        import io as _io
        captured = _io.StringIO()
        with patch("sys.stdout", captured):
            print_summary(result, "some/path.json")
        output = captured.getvalue()
        self.assertIn("executor_oom", output)
        self.assertIn("PASS", output)


# ---------------------------------------------------------------------------
# validate.py helpers
# ---------------------------------------------------------------------------


class TestParseArgs(unittest.TestCase):
    def test_defaults(self) -> None:
        args = parse_args(["--account-id", "123456789012"])
        self.assertFalse(args.skip_run)
        self.assertEqual(args.wait_timeout, 600)
        self.assertEqual(args.poll_interval, 15)
        self.assertIsNone(args.scenario)
        self.assertIsNone(args.context_file)

    def test_skip_run_flag(self) -> None:
        args = parse_args(["--skip-run", "--account-id", "123456789012"])
        self.assertTrue(args.skip_run)

    def test_scenario_flag(self) -> None:
        args = parse_args(["--scenario", "executor_oom", "--account-id", "123456789012"])
        self.assertEqual(args.scenario, "executor_oom")

    def test_mcp_url_flag(self) -> None:
        args = parse_args(["--mcp-url", "http://example.com/mcp", "--account-id", "123456789012"])
        self.assertEqual(args.mcp_url, "http://example.com/mcp")

    def test_wait_timeout_and_poll_interval(self) -> None:
        args = parse_args([
            "--account-id", "123456789012",
            "--wait-timeout", "120",
            "--poll-interval", "5",
        ])
        self.assertEqual(args.wait_timeout, 120)
        self.assertEqual(args.poll_interval, 5)

    def test_log_wait_args(self) -> None:
        args = parse_args([
            "--account-id", "123456789012",
            "--log-wait-timeout", "180",
            "--log-poll-interval", "3",
            "--no-log-wait",
        ])
        self.assertEqual(args.log_wait_timeout, 180)
        self.assertEqual(args.log_poll_interval, 3)
        self.assertTrue(args.no_log_wait)


class TestLoadJson(unittest.TestCase):
    def test_loads_valid_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as f:
            json.dump({"hello": "world"}, f)
            path = f.name
        try:
            data = load_json(path)
            self.assertEqual(data, {"hello": "world"})
        finally:
            Path(path).unlink(missing_ok=True)

    def test_raises_for_missing_file(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_json("/nonexistent/path/file.json")


class TestRunScenario(unittest.TestCase):
    @patch("validation.validate.subprocess.run")
    def test_run_scenario_passes_unique_context_and_run_id(
        self,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value.returncode = 0
        context_file = ROOT / ".harrier-demo" / "runs" / "data_skew-test-run.json"

        run_scenario(
            ROOT,
            "data_skew",
            context_file=context_file,
            run_id="test-run",
        )

        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs["cwd"], ROOT)
        self.assertEqual(kwargs["env"]["CONTEXT_FILE"], str(context_file))
        self.assertEqual(kwargs["env"]["RUN_ID"], "test-run")

    def test_fresh_context_file_is_scenario_scoped(self) -> None:
        context_file = _fresh_context_file(ROOT, "data_skew", "test-run")

        self.assertEqual(
            context_file,
            ROOT / ".harrier-demo" / "runs" / "data_skew-test-run.json",
        )


class TestLogWaitHelpers(unittest.TestCase):
    def _context(self) -> dict:
        return {
            "region": "ap-southeast-2",
            "cluster_id": "j-ABC123",
            "deploy_mode": "cluster",
            "job_state": "failed",
            "step_id": "s-XYZ",
            "application_id": "application_1_0001",
            "log_uri": "s3n://demo-logs/emr/",
        }

    def test_normalize_s3_uri(self) -> None:
        self.assertEqual(normalize_s3_uri("s3n://bucket/logs"), "s3://bucket/logs")
        self.assertEqual(normalize_s3_uri("s3a://bucket/logs"), "s3://bucket/logs")
        self.assertEqual(normalize_s3_uri("s3://bucket/logs"), "s3://bucket/logs")

    def test_listing_has_log_file_handles_recursive_s3_output(self) -> None:
        listing = (
            "2026-01-01 00:00:00       10 "
            "logs/j-ABC/containers/application_1_0001/container_1/stderr.gz\n"
        )
        self.assertTrue(_listing_has_log_file(listing, ("stderr", "stdout")))
        self.assertFalse(_listing_has_log_file(listing, ("syslog",)))

    @patch("validation.validate.export_context")
    @patch("validation.validate.subprocess.check_output")
    def test_wait_for_cluster_logs_requires_step_and_application_logs(
        self,
        mock_check_output: MagicMock,
        mock_export_context: MagicMock,
    ) -> None:
        ctx = self._context()
        mock_export_context.return_value = ctx
        mock_check_output.side_effect = [
            "2026-01-01 00:00:00       10 stderr.gz\n",
            "2026-01-01 00:00:00       10 stdout.gz\n",
        ]

        result = wait_for_emr_s3_logs(
            repo_root=ROOT,
            context_file=ROOT / ".harrier-demo" / "last-context.json",
            exported_file=ROOT / ".harrier-demo" / "last-context-exported.json",
            context=ctx,
            expected_outcome="failed",
            timeout=1,
            poll_interval=1,
        )

        self.assertEqual(result["application_id"], "application_1_0001")
        called_uris = [call.args[0][3] for call in mock_check_output.call_args_list]
        self.assertIn("s3://demo-logs/emr/j-ABC123/steps/s-XYZ/", called_uris)
        self.assertIn(
            "s3://demo-logs/emr/j-ABC123/containers/application_1_0001/",
            called_uris,
        )

    @patch("validation.validate.export_context")
    @patch("validation.validate.subprocess.check_output")
    def test_wait_for_running_outcome_skips_s3_checks(
        self,
        mock_check_output: MagicMock,
        mock_export_context: MagicMock,
    ) -> None:
        ctx = self._context()
        result = wait_for_emr_s3_logs(
            repo_root=ROOT,
            context_file=ROOT / ".harrier-demo" / "last-context.json",
            exported_file=ROOT / ".harrier-demo" / "last-context-exported.json",
            context=ctx,
            expected_outcome="running",
            timeout=1,
            poll_interval=1,
        )

        self.assertIs(result, ctx)
        mock_check_output.assert_not_called()
        mock_export_context.assert_not_called()

    @patch("validation.validate.export_context")
    @patch("validation.validate.subprocess.check_output")
    def test_wait_for_serverless_context_skips_ec2_s3_checks(
        self,
        mock_check_output: MagicMock,
        mock_export_context: MagicMock,
    ) -> None:
        ctx = {
            "runtime": "emr_serverless",
            "region": "ap-southeast-2",
            "serverless_application_id": "00f1app",
            "job_run_id": "00f1app-000001",
            "log_uri": "s3://demo-logs/emr-serverless/",
        }

        result = wait_for_emr_s3_logs(
            repo_root=ROOT,
            context_file=ROOT / ".harrier-demo" / "last-context.json",
            exported_file=ROOT / ".harrier-demo" / "last-context-exported.json",
            context=ctx,
            expected_outcome="failed",
            timeout=1,
            poll_interval=1,
        )

        self.assertIs(result, ctx)
        mock_check_output.assert_not_called()
        mock_export_context.assert_not_called()


class TestServerlessWaitHelper(unittest.TestCase):
    @patch("validation.validate.subprocess.check_output")
    def test_wait_for_serverless_job_returns_terminal_state(self, mock_check_output: MagicMock) -> None:
        mock_check_output.side_effect = ["RUNNING", "SUCCESS"]

        result = wait_for_serverless_job(
            "00f1app",
            "00f1app-000001",
            "ap-southeast-2",
            timeout=2,
            poll_interval=0,
        )

        self.assertEqual(result, "SUCCESS")
        command = mock_check_output.call_args_list[-1].args[0]
        self.assertIn("emr-serverless", command)
        self.assertIn("get-job-run", command)
        self.assertIn("00f1app-000001", command)


class TestEksWaitHelper(unittest.TestCase):
    @patch("validation.validate.subprocess.check_output")
    def test_wait_for_eks_job_returns_terminal_state(self, mock_check_output: MagicMock) -> None:
        mock_check_output.side_effect = ["RUNNING", "FAILED"]

        result = wait_for_eks_job(
            "vc-1234567890abcdef0",
            "job-run-123",
            "ap-southeast-2",
            timeout=2,
            poll_interval=0,
        )

        self.assertEqual(result, "FAILED")
        command = mock_check_output.call_args_list[-1].args[0]
        self.assertIn("emr-containers", command)
        self.assertIn("describe-job-run", command)
        self.assertIn("vc-1234567890abcdef0", command)
        self.assertIn("job-run-123", command)


class TestBuildMcpRequest(unittest.TestCase):
    def _context(self) -> dict:
        return {
            "region": "ap-southeast-2",
            "cluster_id": "j-ABC123",
            "deploy_mode": "cluster",
            "job_state": "failed",
            "step_id": "s-XYZ",
            "application_id": "application_1_0001",
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "log_uri": "s3://bucket/logs/",
            "diagnostic_signals": None,
        }

    def test_basic_fields_are_included(self) -> None:
        req = build_mcp_request(self._context(), "123456789012")
        self.assertEqual(req["account_id"], "123456789012")
        self.assertEqual(req["region"], "ap-southeast-2")
        self.assertEqual(req["cluster_id"], "j-ABC123")
        self.assertEqual(req["deploy_mode"], "cluster")
        self.assertEqual(req["job_state"], "failed")
        self.assertEqual(req["step_id"], "s-XYZ")
        self.assertEqual(req["application_id"], "application_1_0001")

    def test_log_uri_not_in_request(self) -> None:
        # harrier_start_emr_investigation has no log_uri parameter
        req = build_mcp_request(self._context(), "123456789012")
        self.assertNotIn("log_uri", req)

    def test_time_window_included_when_present(self) -> None:
        req = build_mcp_request(self._context(), "123456789012")
        self.assertIn("time_window", req)
        self.assertEqual(req["time_window"]["start"], "2026-01-01T00:00:00Z")

    def test_valid_diagnostic_signals_are_included(self) -> None:
        ctx = self._context()
        ctx["diagnostic_signals"] = {
            "active_stage_count": 1,
            "skew_ratio": 12,
            "root_cause_hint": "DATA_SKEW",  # should be filtered out
            "log_signal": "something",         # should be filtered out
        }
        req = build_mcp_request(ctx, "123456789012")
        signals = req["diagnostic_signals"]
        self.assertEqual(signals["active_stage_count"], 1)
        self.assertEqual(signals["skew_ratio"], 12)
        self.assertNotIn("root_cause_hint", signals)
        self.assertNotIn("log_signal", signals)

    def test_unrecognised_only_signals_omitted_entirely(self) -> None:
        ctx = self._context()
        ctx["diagnostic_signals"] = {
            "root_cause_hint": "EXECUTOR_OOM",
            "executor_memory_allocation_mb": 768,
            "log_signal": "OOM",
        }
        req = build_mcp_request(ctx, "123456789012")
        self.assertNotIn("diagnostic_signals", req)

    def test_none_diagnostic_signals_not_included(self) -> None:
        ctx = self._context()
        ctx["diagnostic_signals"] = None
        req = build_mcp_request(ctx, "123456789012")
        self.assertNotIn("diagnostic_signals", req)

    def test_step_id_omitted_when_empty(self) -> None:
        ctx = self._context()
        ctx["step_id"] = ""
        req = build_mcp_request(ctx, "123456789012")
        self.assertNotIn("step_id", req)

    def test_application_id_omitted_when_none(self) -> None:
        ctx = self._context()
        ctx["application_id"] = None
        req = build_mcp_request(ctx, "123456789012")
        self.assertNotIn("application_id", req)

    def test_serverless_runtime_uses_typed_target(self) -> None:
        ctx = {
            "runtime": "emr_serverless",
            "region": "ap-southeast-2",
            "serverless_application_id": "00f1abcd2efg3hij",
            "job_run_id": "00f1abcd2efg3hij-000001",
            "attempt": 1,
            "job_state": "failed",
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "diagnostic_signals": {
                "active_stage_count": 1,
                "root_cause_hint": "EXECUTOR_OOM",
            },
        }

        req = build_mcp_request(ctx, "123456789012")

        self.assertEqual(req["account_id"], "123456789012")
        self.assertEqual(req["runtime"], "emr_serverless")
        self.assertEqual(req["target"]["serverless_application_id"], "00f1abcd2efg3hij")
        self.assertEqual(req["target"]["job_run_id"], "00f1abcd2efg3hij-000001")
        self.assertEqual(req["target"]["attempt"], 1)
        self.assertEqual(req["job_state"], "failed")
        self.assertNotIn("cluster_id", req)
        self.assertNotIn("step_id", req)
        self.assertEqual(req["diagnostic_signals"], {"active_stage_count": 1})

    def test_eks_runtime_uses_typed_target(self) -> None:
        ctx = {
            "runtime": "emr_eks",
            "region": "ap-southeast-2",
            "virtual_cluster_id": "vc-1234567890abcdef0",
            "job_run_id": "job-run-123",
            "eks_cluster_name": "analytics-dev",
            "namespace": "harrier-emr-jobs",
            "job_state": "failed",
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "diagnostic_signals": {
                "active_stage_count": 1,
                "root_cause_hint": "EKS_POD_PENDING",
            },
        }

        req = build_mcp_request(ctx, "123456789012")

        self.assertEqual(req["account_id"], "123456789012")
        self.assertEqual(req["runtime"], "emr_eks")
        self.assertEqual(req["target"]["virtual_cluster_id"], "vc-1234567890abcdef0")
        self.assertEqual(req["target"]["job_run_id"], "job-run-123")
        self.assertEqual(req["target"]["eks_cluster_name"], "analytics-dev")
        self.assertEqual(req["target"]["namespace"], "harrier-emr-jobs")
        self.assertEqual(req["job_state"], "failed")
        self.assertNotIn("cluster_id", req)
        self.assertNotIn("step_id", req)
        self.assertEqual(req["diagnostic_signals"], {"active_stage_count": 1})


class TestRunningSignalFields(unittest.TestCase):
    def test_known_fields_are_in_set(self) -> None:
        for field in (
            "active_stage_count",
            "skew_ratio",
            "shuffle_spill_mb",
            "jdbc_stage_active",
            "db_plan_summary",
            "yarn_memory_available_percent",
        ):
            self.assertIn(field, _RUNNING_SIGNAL_FIELDS)

    def test_scenario_specific_fields_are_not_in_set(self) -> None:
        for field in ("root_cause_hint", "log_signal", "executor_memory_allocation_mb"):
            self.assertNotIn(field, _RUNNING_SIGNAL_FIELDS)


# ---------------------------------------------------------------------------
# Module-level smoke tests
# ---------------------------------------------------------------------------


class TestModuleImports(unittest.TestCase):
    def test_validate_module_has_main(self) -> None:
        from validation import validate
        self.assertTrue(callable(validate.main))

    def test_validate_module_has_build_mcp_request(self) -> None:
        from validation import validate
        self.assertTrue(callable(validate.build_mcp_request))

    def test_harrier_client_is_importable(self) -> None:
        from validation.harrier_client import HarrierClient, HarrierClientError
        client = HarrierClient(mcp_url="http://localhost:9999/mcp")
        self.assertEqual(client.mcp_url, "http://localhost:9999/mcp")

    def test_compare_is_importable(self) -> None:
        from validation.compare import compare
        self.assertTrue(callable(compare))

    def test_report_functions_are_importable(self) -> None:
        from validation.report import format_report, write_report
        self.assertTrue(callable(format_report))
        self.assertTrue(callable(write_report))


# ---------------------------------------------------------------------------
# Script content checks (no execution)
# ---------------------------------------------------------------------------


class TestValidateScenarioSh(unittest.TestCase):
    _SCRIPT = ROOT / "scripts" / "validate_scenario.sh"

    def test_script_exists(self) -> None:
        self.assertTrue(self._SCRIPT.is_file())

    def test_script_calls_validate_py(self) -> None:
        content = self._SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate.py", content)

    def test_script_passes_scenario_argument(self) -> None:
        content = self._SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--scenario", content)

    def test_script_has_usage_comment(self) -> None:
        content = self._SCRIPT.read_text(encoding="utf-8")
        self.assertIn("HARRIER_MCP_URL", content)
        self.assertIn("AWS_ACCOUNT_ID", content)

    def test_script_documents_skip_scenario_run(self) -> None:
        content = self._SCRIPT.read_text(encoding="utf-8")
        self.assertIn("SKIP_SCENARIO_RUN", content)

    def test_script_uses_configurable_python(self) -> None:
        content = self._SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PYTHON_BIN", content)
        self.assertNotIn("/usr/local/bin/python3.10", content)


# ---------------------------------------------------------------------------
# Expected findings schema sanity check
# ---------------------------------------------------------------------------


class TestExpectedFindingsSchema(unittest.TestCase):
    """Every expected-findings file must be parseable and have required keys."""

    _FINDINGS_DIR = ROOT / "expected-findings"

    def test_all_scenario_files_are_valid_json(self) -> None:
        for path in sorted(self._FINDINGS_DIR.glob("*.json")):
            with self.subTest(scenario=path.stem):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(data, dict)
                self.assertEqual(data.get("scenario"), path.stem)

    def test_non_happy_path_files_have_root_cause_category(self) -> None:
        for path in sorted(self._FINDINGS_DIR.glob("*.json")):
            with self.subTest(scenario=path.stem):
                data = json.loads(path.read_text(encoding="utf-8"))
                if path.stem == "happy_path":
                    self.assertNotIn("expected_root_cause_category", data)
                else:
                    self.assertIn("expected_root_cause_category", data)

    def test_all_files_have_expected_outcome(self) -> None:
        for path in sorted(self._FINDINGS_DIR.glob("*.json")):
            with self.subTest(scenario=path.stem):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn(
                    data.get("expected_outcome"),
                    {"success", "failed", "running"},
                )


if __name__ == "__main__":
    unittest.main()
