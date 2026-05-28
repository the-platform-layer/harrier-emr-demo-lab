#!/usr/bin/env python3
"""Scenario validation harness for Harrier EMR Demo Lab.

Runs one demo scenario end-to-end:
  1. Optionally submits the scenario (scripts/run_scenario.sh).
  2. Exports the investigation context (scripts/export_investigation_context.sh).
  3. Waits for the EMR step to reach a terminal state (skipped for running-job scenarios).
  4. Calls the already-running Harrier MCP server.
  5. Compares the actual root cause against expected-findings/<scenario>.json.
  6. Writes a validation report to .harrier-demo/validation/<scenario>-<ts>.json.
  7. Exits 0 on pass, 1 on fail, 2 on configuration error.

Required env vars
  HARRIER_MCP_URL     URL of the running Harrier MCP server
                      (default: http://localhost:8000/mcp)
  AWS_ACCOUNT_ID      12-digit AWS account ID for the investigation request

Optional env vars
  SKIP_SCENARIO_RUN   Set to 1 to skip scripts/run_scenario.sh
  CLUSTER_ID          Override cluster_id read from context file
  AWS_REGION          Override region read from context file
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from validation.compare import compare
from validation.harrier_client import HarrierClient, HarrierClientError
from validation.report import write_report

# Fields accepted by RunningJobDiagnosticSignals in the MCP server
_RUNNING_SIGNAL_FIELDS = frozenset({
    "elapsed_minutes",
    "active_stage_count",
    "active_task_count",
    "max_task_runtime_minutes",
    "median_task_runtime_minutes",
    "skew_ratio",
    "shuffle_spill_mb",
    "input_gb",
    "pending_containers",
    "yarn_memory_available_percent",
    "executor_failures",
    "node_unhealthy_count",
    "jdbc_stage_active",
    "active_db_query_seconds",
    "db_wait_event",
    "db_plan_summary",
})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Harrier scenario validation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scenario", help="Scenario name")
    parser.add_argument(
        "--context-file",
        help="Path to investigation context JSON "
             "(default: .harrier-demo/last-context.json)",
    )
    parser.add_argument(
        "--expected-findings",
        help="Path to expected findings JSON "
             "(default: expected-findings/<scenario>.json)",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.environ.get("HARRIER_MCP_URL", "http://localhost:8000/mcp"),
        help="Harrier MCP URL (env: HARRIER_MCP_URL)",
    )
    parser.add_argument(
        "--account-id",
        default=os.environ.get("AWS_ACCOUNT_ID", ""),
        help="12-digit AWS account ID (env: AWS_ACCOUNT_ID)",
    )
    parser.add_argument(
        "--output",
        help="Validation report output path",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        default=os.environ.get("SKIP_SCENARIO_RUN", "0") == "1",
        help="Skip scripts/run_scenario.sh (env: SKIP_SCENARIO_RUN=1)",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=600,
        metavar="SECONDS",
        help="Max seconds to wait for step terminal state (default: 600)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=15,
        metavar="SECONDS",
        help="Step polling interval in seconds (default: 15)",
    )
    return parser.parse_args(argv)


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def run_scenario(repo_root: Path, scenario: str) -> None:
    script = repo_root / "scripts" / "run_scenario.sh"
    result = subprocess.run(
        ["bash", str(script), scenario],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"run_scenario.sh exited {result.returncode} for {scenario!r}")


def export_context(
    repo_root: Path,
    context_file: Path,
    output_file: Path,
) -> dict[str, Any]:
    script = repo_root / "scripts" / "export_investigation_context.sh"
    result = subprocess.run(
        [
            "bash", str(script),
            "--context-file", str(context_file),
            "--output", str(output_file),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"export_investigation_context.sh failed: {result.stderr.strip()}"
        )
    return load_json(output_file)


def wait_for_step(
    cluster_id: str,
    step_id: str,
    region: str,
    timeout: int = 600,
    poll_interval: int = 15,
) -> str:
    """Poll EMR describe-step until a terminal state; return the final state string."""
    terminal = {"COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = subprocess.check_output(
                [
                    "aws", "emr", "describe-step",
                    "--cluster-id", cluster_id,
                    "--step-id", step_id,
                    "--region", region,
                    "--query", "Step.Status.State",
                    "--output", "text",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except subprocess.CalledProcessError:
            state = ""
        if state in terminal:
            return state
        remaining = max(0, int(deadline - time.monotonic()))
        print(
            f"  Step {step_id}: {state or '(unknown)'}. "
            f"Waiting… ({remaining}s remaining)"
        )
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Step {step_id} did not reach terminal state within {timeout}s"
    )


def build_mcp_request(
    context: dict[str, Any],
    account_id: str,
) -> dict[str, Any]:
    """Build harrier_start_emr_investigation arguments from investigation context.

    Filters diagnostic_signals to only include fields accepted by
    RunningJobDiagnosticSignals; scenario-specific fields like root_cause_hint
    and log_signal are dropped.
    """
    req: dict[str, Any] = {
        "account_id": account_id,
        "region": context.get("region", ""),
        "cluster_id": context.get("cluster_id", ""),
        "deploy_mode": context.get("deploy_mode", "unknown"),
        "job_state": context.get("job_state", "unknown"),
    }

    if context.get("step_id"):
        req["step_id"] = context["step_id"]

    if context.get("application_id"):
        req["application_id"] = context["application_id"]

    time_window = context.get("time_window")
    if time_window and isinstance(time_window, dict):
        req["time_window"] = time_window

    raw_signals = context.get("diagnostic_signals")
    if raw_signals and isinstance(raw_signals, dict):
        filtered = {k: v for k, v in raw_signals.items() if k in _RUNNING_SIGNAL_FIELDS}
        if filtered:
            req["diagnostic_signals"] = filtered

    return req


def _default_output(repo_root: Path, scenario: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return repo_root / ".harrier-demo" / "validation" / f"{scenario}-{ts}.json"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = _REPO_ROOT

    default_context_file = repo_root / ".harrier-demo" / "last-context.json"
    context_file = Path(args.context_file) if args.context_file else default_context_file

    # ------------------------------------------------------------------
    # Step 1: Optionally submit the scenario
    # ------------------------------------------------------------------
    if not args.skip_run:
        scenario_to_run = args.scenario
        if not scenario_to_run:
            if context_file.is_file():
                scenario_to_run = load_json(context_file).get("scenario", "happy_path")
            else:
                scenario_to_run = "happy_path"
        print(f"Submitting scenario: {scenario_to_run}")
        run_scenario(repo_root, scenario_to_run)

    # ------------------------------------------------------------------
    # Step 2: Export investigation context (enriches with live step state)
    # ------------------------------------------------------------------
    exported_file = context_file.parent / (context_file.stem + "-exported.json")
    print("Exporting investigation context…")
    try:
        context = export_context(repo_root, context_file, exported_file)
    except (FileNotFoundError, RuntimeError) as exc:
        if not context_file.is_file():
            print(f"ERROR: Context file not found: {context_file}", file=sys.stderr)
            return 2
        print(f"  Warning: export failed ({exc}). Using context file directly.")
        context = load_json(context_file)

    scenario: str = args.scenario or context.get("scenario", "happy_path")
    print(f"Scenario  : {scenario}")
    print(f"Cluster   : {context.get('cluster_id', '(none)')}")
    print(f"Step      : {context.get('step_id', '(none)')}")

    # ------------------------------------------------------------------
    # Step 3: Load expected findings
    # ------------------------------------------------------------------
    expected_path = (
        Path(args.expected_findings)
        if args.expected_findings
        else repo_root / "expected-findings" / f"{scenario}.json"
    )
    if not expected_path.is_file():
        print(f"ERROR: Expected findings not found: {expected_path}", file=sys.stderr)
        return 2
    expected = load_json(expected_path)
    expected_outcome: str = expected.get("expected_outcome", "failed")

    # ------------------------------------------------------------------
    # Step 4: Wait for terminal state (skip for running-job scenarios)
    # ------------------------------------------------------------------
    cluster_id = context.get("cluster_id", "")
    step_id = context.get("step_id", "")
    region = context.get("region", "")

    if (
        expected_outcome != "running"
        and cluster_id
        and step_id
        and region
        and not args.skip_run
    ):
        print(f"Waiting for step {step_id} to complete…")
        try:
            final_state = wait_for_step(
                cluster_id,
                step_id,
                region,
                timeout=args.wait_timeout,
                poll_interval=args.poll_interval,
            )
            print(f"  Step state: {final_state}")
            context = export_context(repo_root, context_file, exported_file)
        except (TimeoutError, RuntimeError) as exc:
            print(f"  Warning: {exc}. Proceeding with current context.")

    # ------------------------------------------------------------------
    # Step 5: Call Harrier MCP
    # ------------------------------------------------------------------
    account_id = args.account_id
    if not account_id:
        print("ERROR: --account-id or AWS_ACCOUNT_ID is required", file=sys.stderr)
        return 2

    mcp_url = args.mcp_url
    print(f"Calling Harrier MCP: {mcp_url}")
    client = HarrierClient(mcp_url=mcp_url, timeout=120)
    try:
        client.initialize()
    except HarrierClientError as exc:
        print(f"ERROR: MCP initialize failed: {exc}", file=sys.stderr)
        return 2

    mcp_args = build_mcp_request(context, account_id)
    print(f"  Starting investigation (cluster={mcp_args.get('cluster_id')})…")
    try:
        actual = client.call_tool("harrier_start_emr_investigation", mcp_args)
    except HarrierClientError as exc:
        print(f"ERROR: MCP tool call failed: {exc}", file=sys.stderr)
        return 2

    print(f"  Investigation ID: {actual.get('investigation_id', '(none)')}")

    # ------------------------------------------------------------------
    # Step 6 & 7: Compare and write report
    # ------------------------------------------------------------------
    result = compare(expected, actual)
    output_path = Path(args.output) if args.output else _default_output(repo_root, scenario)
    write_report(result, output_path)

    return 0 if result.outcome == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
