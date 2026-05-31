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
  CONTEXT_FILE         Context file path for fresh scenario submission
  RUN_ID               Run identifier for fresh scenario submission
  RUNTIME              emr_ec2, emr_serverless, or emr_eks for fresh scenario submission
  CLUSTER_ID          Override cluster_id read from context file
  AWS_REGION          Override region read from context file
  LOG_WAIT_TIMEOUT    Max seconds to wait for EMR logs in S3
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
    parser.add_argument(
        "--log-wait-timeout",
        type=int,
        default=int(os.environ.get("LOG_WAIT_TIMEOUT", "420")),
        metavar="SECONDS",
        help="Max seconds to wait for EMR S3 logs before calling MCP (default: 420)",
    )
    parser.add_argument(
        "--log-poll-interval",
        type=int,
        default=int(os.environ.get("LOG_POLL_INTERVAL", "30")),
        metavar="SECONDS",
        help="S3 log polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--no-log-wait",
        action="store_true",
        default=os.environ.get("NO_LOG_WAIT", "0") == "1",
        help="Do not wait for EMR logs in S3 before calling MCP",
    )
    return parser.parse_args(argv)


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def run_scenario(
    repo_root: Path,
    scenario: str,
    *,
    context_file: Path | None = None,
    run_id: str | None = None,
) -> None:
    script = repo_root / "scripts" / "run_scenario.sh"
    env = os.environ.copy()
    if context_file is not None:
        env["CONTEXT_FILE"] = str(context_file)
    if run_id is not None:
        env["RUN_ID"] = run_id
    result = subprocess.run(
        ["bash", str(script), scenario],
        cwd=repo_root,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"run_scenario.sh exited {result.returncode} for {scenario!r}")


def _fresh_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{os.getpid()}"


def _fresh_context_file(repo_root: Path, scenario: str, run_id: str) -> Path:
    return repo_root / ".harrier-demo" / "runs" / f"{scenario}-{run_id}.json"


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


def wait_for_serverless_job(
    application_id: str,
    job_run_id: str,
    region: str,
    timeout: int = 600,
    poll_interval: int = 15,
) -> str:
    """Poll EMR Serverless get-job-run until a terminal state."""
    terminal = {"SUCCESS", "FAILED", "CANCELLED"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = subprocess.check_output(
                [
                    "aws", "emr-serverless", "get-job-run",
                    "--application-id", application_id,
                    "--job-run-id", job_run_id,
                    "--region", region,
                    "--query", "jobRun.state",
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
            f"  Serverless job {job_run_id}: {state or '(unknown)'}. "
            f"Waiting… ({remaining}s remaining)"
        )
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Serverless job {job_run_id} did not reach terminal state within {timeout}s"
    )


def wait_for_eks_job(
    virtual_cluster_id: str,
    job_run_id: str,
    region: str,
    timeout: int = 600,
    poll_interval: int = 15,
) -> str:
    """Poll EMR Containers describe-job-run until a terminal state."""
    terminal = {"COMPLETED", "FAILED", "CANCELLED"}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = subprocess.check_output(
                [
                    "aws", "emr-containers", "describe-job-run",
                    "--virtual-cluster-id", virtual_cluster_id,
                    "--id", job_run_id,
                    "--region", region,
                    "--query", "jobRun.state",
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
            f"  EMR on EKS job {job_run_id}: {state or '(unknown)'}. "
            f"Waiting… ({remaining}s remaining)"
        )
        time.sleep(poll_interval)
    raise TimeoutError(
        f"EMR on EKS job {job_run_id} did not reach terminal state within {timeout}s"
    )


def wait_for_eks_pod_signal(
    *,
    namespace: str,
    job_run_id: str,
    expected_category: str,
    timeout: int = 600,
    poll_interval: int = 15,
) -> bool:
    """Wait for live Kubernetes pod evidence before EMR cleans up failed pods."""
    if expected_category not in {"EKS_IMAGE_PULL_FAILURE", "EKS_POD_PENDING"}:
        return False
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pods = _eks_job_pods(namespace=namespace, job_run_id=job_run_id)
        if _pods_have_expected_signal(pods, expected_category):
            return True
        remaining = max(0, int(deadline - time.monotonic()))
        pod_summary = ", ".join(
            f"{pod.get('metadata', {}).get('name', 'unknown')}:{pod.get('status', {}).get('phase', 'unknown')}"
            for pod in pods
        ) or "no matching pods"
        print(
            f"  EKS pod signal for {expected_category}: {pod_summary}. "
            f"Waiting... ({remaining}s remaining)"
        )
        time.sleep(poll_interval)
    return False


def _eks_job_pods(*, namespace: str, job_run_id: str) -> list[dict[str, Any]]:
    try:
        output = subprocess.check_output(
            ["kubectl", "get", "pods", "-n", namespace, "-o", "json"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    try:
        items = json.loads(output).get("items", [])
    except json.JSONDecodeError:
        return []
    return [pod for pod in items if _pod_matches_job(pod, job_run_id)]


def _pod_matches_job(pod: dict[str, Any], job_run_id: str) -> bool:
    metadata = pod.get("metadata", {})
    labels = metadata.get("labels") or {}
    annotations = metadata.get("annotations") or {}
    haystack = " ".join(
        [
            str(metadata.get("name", "")),
            *[str(item) for pair in labels.items() for item in pair],
            *[str(item) for pair in annotations.items() for item in pair],
        ]
    )
    return job_run_id in haystack


def _pods_have_expected_signal(pods: list[dict[str, Any]], expected_category: str) -> bool:
    for pod in pods:
        status = pod.get("status", {})
        if expected_category == "EKS_POD_PENDING":
            if status.get("phase") == "Pending":
                return True
            for condition in status.get("conditions", []) or []:
                if (
                    condition.get("type") == "PodScheduled"
                    and str(condition.get("status", "")).lower() == "false"
                    and condition.get("reason") == "Unschedulable"
                ):
                    return True
        if expected_category == "EKS_IMAGE_PULL_FAILURE":
            for container in status.get("containerStatuses", []) or []:
                waiting = (container.get("state") or {}).get("waiting") or {}
                if waiting.get("reason") in {"ErrImagePull", "ImagePullBackOff"}:
                    return True
    return False


def normalize_s3_uri(uri: str) -> str:
    """Normalize Hadoop S3 schemes to an aws-cli-compatible s3:// URI."""
    for legacy in ("s3n://", "s3a://"):
        if uri.startswith(legacy):
            return "s3://" + uri[len(legacy):]
    return uri


def _s3_ls(uri: str, region: str, *, recursive: bool = False) -> str:
    command = ["aws", "s3", "ls", normalize_s3_uri(uri), "--region", region]
    if recursive:
        command.append("--recursive")
    return subprocess.check_output(
        command,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _listing_has_log_file(listing: str, names: tuple[str, ...]) -> bool:
    for line in listing.splitlines():
        filename = line.rsplit(None, 1)[-1].rsplit("/", 1)[-1]
        if any(filename.startswith(name) for name in names):
            return True
    return False


def _has_step_logs(log_uri: str, cluster_id: str, step_id: str, region: str) -> bool:
    step_uri = f"{normalize_s3_uri(log_uri).rstrip('/')}/{cluster_id}/steps/{step_id}/"
    try:
        listing = _s3_ls(step_uri, region)
    except subprocess.CalledProcessError:
        return False
    return _listing_has_log_file(listing, ("stderr", "stdout", "controller", "syslog"))


def _has_application_logs(log_uri: str, cluster_id: str, application_id: str, region: str) -> bool:
    app_uri = f"{normalize_s3_uri(log_uri).rstrip('/')}/{cluster_id}/containers/{application_id}/"
    try:
        listing = _s3_ls(app_uri, region, recursive=True)
    except subprocess.CalledProcessError:
        return False
    return _listing_has_log_file(listing, ("stderr", "stdout", "syslog"))


def _has_serverless_s3_logs(
    log_uri: str,
    application_id: str,
    job_run_id: str,
    region: str,
) -> bool:
    job_uri = (
        f"{normalize_s3_uri(log_uri).rstrip('/')}/"
        f"applications/{application_id}/jobs/{job_run_id}/"
    )
    try:
        listing = _s3_ls(job_uri, region, recursive=True)
    except subprocess.CalledProcessError:
        return False
    return _listing_has_log_file(listing, ("stderr", "stdout", "job-metadata"))


def _has_cloudwatch_log_streams(
    log_group: str,
    log_stream_prefix: str,
    region: str,
) -> bool:
    if not (log_group and log_stream_prefix and region):
        return False
    try:
        output = subprocess.check_output(
            [
                "aws", "logs", "describe-log-streams",
                "--log-group-name", log_group,
                "--log-stream-name-prefix", log_stream_prefix,
                "--region", region,
                "--query", "length(logStreams)",
                "--output", "text",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return False
    try:
        return int(output) > 0
    except ValueError:
        return False


def wait_for_emr_s3_logs(
    *,
    repo_root: Path,
    context_file: Path,
    exported_file: Path,
    context: dict[str, Any],
    expected_outcome: str,
    timeout: int = 420,
    poll_interval: int = 30,
) -> dict[str, Any]:
    """Wait for EMR step/container logs to be visible in S3.

    EMR step state can become terminal before the archived logs are readable.
    Cluster deploy mode is especially laggy because the Python exception is
    usually in YARN container stdout/stderr rather than the step wrapper logs.
    """
    if context.get("runtime", "emr_ec2") != "emr_ec2":
        return context

    if expected_outcome == "running":
        return context

    cluster_id = context.get("cluster_id", "")
    step_id = context.get("step_id", "")
    region = context.get("region", "")
    log_uri = context.get("log_uri", "")
    deploy_mode = context.get("deploy_mode", "unknown")

    if not (cluster_id and step_id and region and log_uri):
        return context

    deadline = time.monotonic() + timeout
    latest_context = context
    while time.monotonic() < deadline:
        step_ready = _has_step_logs(log_uri, cluster_id, step_id, region)
        app_ready = True
        application_id = latest_context.get("application_id")

        if deploy_mode == "cluster" and expected_outcome == "failed":
            if not application_id:
                try:
                    latest_context = export_context(repo_root, context_file, exported_file)
                    application_id = latest_context.get("application_id")
                except (FileNotFoundError, RuntimeError):
                    application_id = None
            app_ready = bool(application_id) and _has_application_logs(
                log_uri,
                cluster_id,
                application_id,
                region,
            )

        if step_ready and app_ready:
            try:
                return export_context(repo_root, context_file, exported_file)
            except (FileNotFoundError, RuntimeError):
                return latest_context

        remaining = max(0, int(deadline - time.monotonic()))
        app_label = application_id or "(not inferred yet)"
        print(
            "  Waiting for EMR S3 logs "
            f"(step_logs={step_ready}, app_logs={app_ready}, app={app_label}; "
            f"{remaining}s remaining)"
        )
        time.sleep(poll_interval)

    print("  Warning: EMR S3 logs were not fully available before timeout.")
    return latest_context


def wait_for_serverless_logs(
    *,
    repo_root: Path,
    context_file: Path,
    exported_file: Path,
    context: dict[str, Any],
    expected_outcome: str,
    timeout: int = 420,
    poll_interval: int = 30,
) -> dict[str, Any]:
    """Wait for EMR Serverless S3 or CloudWatch logs to be discoverable."""
    if context.get("runtime") != "emr_serverless":
        return context

    if expected_outcome == "running":
        return context

    application_id = context.get("serverless_application_id", "")
    job_run_id = context.get("job_run_id", "")
    region = context.get("region", "")
    log_uri = context.get("log_uri", "")
    log_group = context.get("cloudwatch_log_group", "")
    log_stream_prefix = context.get("cloudwatch_log_stream_prefix", "")

    if not (application_id and job_run_id and region):
        return context

    expected_stream_prefix = (
        f"{log_stream_prefix.strip('/')}/applications/{application_id}/jobs/{job_run_id}"
        if log_stream_prefix
        else ""
    )
    deadline = time.monotonic() + timeout
    latest_context = context
    while time.monotonic() < deadline:
        s3_ready = bool(log_uri) and _has_serverless_s3_logs(
            log_uri,
            application_id,
            job_run_id,
            region,
        )
        cloudwatch_ready = bool(log_group and expected_stream_prefix) and _has_cloudwatch_log_streams(
            log_group,
            expected_stream_prefix,
            region,
        )

        if cloudwatch_ready or s3_ready:
            try:
                return export_context(repo_root, context_file, exported_file)
            except (FileNotFoundError, RuntimeError):
                return latest_context

        remaining = max(0, int(deadline - time.monotonic()))
        print(
            "  Waiting for EMR Serverless logs "
            f"(s3_logs={s3_ready}, cloudwatch_logs={cloudwatch_ready}; "
            f"{remaining}s remaining)"
        )
        time.sleep(poll_interval)

    print("  Warning: EMR Serverless logs were not available before timeout.")
    return latest_context


def build_mcp_request(
    context: dict[str, Any],
    account_id: str,
) -> dict[str, Any]:
    """Build harrier_start_emr_investigation arguments from investigation context.

    Filters diagnostic_signals to only include fields accepted by
    RunningJobDiagnosticSignals; scenario-specific fields like root_cause_hint
    and log_signal are dropped.
    """
    runtime = context.get("runtime", "emr_ec2")

    if runtime in {"emr_serverless", "serverless"}:
        target = dict(context.get("target") or {})
        serverless_application_id = (
            target.get("serverless_application_id")
            or context.get("serverless_application_id")
        )
        job_run_id = target.get("job_run_id") or context.get("job_run_id")
        attempt = target.get("attempt", context.get("attempt"))
        req = {
            "account_id": account_id,
            "region": context.get("region", ""),
            "runtime": "emr_serverless",
            "target": {
                "serverless_application_id": serverless_application_id,
                "job_run_id": job_run_id,
            },
            "job_state": context.get("job_state", "unknown"),
        }
        if attempt not in (None, ""):
            req["target"]["attempt"] = int(attempt)

        time_window = context.get("time_window")
        if time_window and isinstance(time_window, dict):
            req["time_window"] = time_window

        raw_signals = context.get("diagnostic_signals")
        if raw_signals and isinstance(raw_signals, dict):
            filtered = {k: v for k, v in raw_signals.items() if k in _RUNNING_SIGNAL_FIELDS}
            if filtered:
                req["diagnostic_signals"] = filtered

        return req

    if runtime in {"emr_eks", "eks"}:
        target = dict(context.get("target") or {})
        virtual_cluster_id = (
            target.get("virtual_cluster_id")
            or context.get("virtual_cluster_id")
        )
        job_run_id = target.get("job_run_id") or context.get("job_run_id")
        eks_cluster_name = target.get("eks_cluster_name") or context.get("eks_cluster_name")
        namespace = target.get("namespace") or context.get("namespace")
        req = {
            "account_id": account_id,
            "region": context.get("region", ""),
            "runtime": "emr_eks",
            "target": {
                "virtual_cluster_id": virtual_cluster_id,
                "job_run_id": job_run_id,
            },
            "job_state": context.get("job_state", "unknown"),
        }
        if eks_cluster_name:
            req["target"]["eks_cluster_name"] = eks_cluster_name
        if namespace:
            req["target"]["namespace"] = namespace

        time_window = context.get("time_window")
        if time_window and isinstance(time_window, dict):
            req["time_window"] = time_window

        raw_signals = context.get("diagnostic_signals")
        if raw_signals and isinstance(raw_signals, dict):
            filtered = {k: v for k, v in raw_signals.items() if k in _RUNNING_SIGNAL_FIELDS}
            if filtered:
                req["diagnostic_signals"] = filtered

        return req

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
        run_id = os.environ.get("RUN_ID") or _fresh_run_id()
        if not args.context_file:
            context_file = _fresh_context_file(repo_root, scenario_to_run, run_id)
        print(f"Submitting scenario: {scenario_to_run}")
        run_scenario(
            repo_root,
            scenario_to_run,
            context_file=context_file,
            run_id=run_id,
        )

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
    runtime: str = context.get("runtime", "emr_ec2")
    print(f"Scenario  : {scenario}")
    print(f"Runtime   : {runtime}")
    if runtime == "emr_serverless":
        print(f"App       : {context.get('serverless_application_id', '(none)')}")
        print(f"Job run   : {context.get('job_run_id', '(none)')}")
    elif runtime == "emr_eks":
        print(f"Virtual cluster: {context.get('virtual_cluster_id', '(none)')}")
        print(f"Job run        : {context.get('job_run_id', '(none)')}")
        print(f"EKS cluster    : {context.get('eks_cluster_name', '(none)')}")
        print(f"Namespace      : {context.get('namespace', '(none)')}")
    else:
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
    expected_category: str = expected.get("expected_root_cause_category", "")

    # ------------------------------------------------------------------
    # Step 4: Wait for terminal state (skip for running-job scenarios)
    # ------------------------------------------------------------------
    cluster_id = context.get("cluster_id", "")
    step_id = context.get("step_id", "")
    serverless_application_id = context.get("serverless_application_id", "")
    job_run_id = context.get("job_run_id", "")
    virtual_cluster_id = context.get("virtual_cluster_id", "")
    region = context.get("region", "")

    if (
        expected_outcome != "running"
        and runtime == "emr_serverless"
        and serverless_application_id
        and job_run_id
        and region
        and not args.skip_run
    ):
        print(f"Waiting for Serverless job run {job_run_id} to complete…")
        try:
            final_state = wait_for_serverless_job(
                serverless_application_id,
                job_run_id,
                region,
                timeout=args.wait_timeout,
                poll_interval=args.poll_interval,
            )
            print(f"  Serverless job state: {final_state}")
            context = export_context(repo_root, context_file, exported_file)
        except (TimeoutError, RuntimeError) as exc:
            print(f"  Warning: {exc}. Proceeding with current context.")
    elif (
        expected_outcome != "running"
        and runtime == "emr_eks"
        and virtual_cluster_id
        and job_run_id
        and region
        and not args.skip_run
    ):
        namespace = context.get("namespace", "")
        if namespace and expected_category in {"EKS_IMAGE_PULL_FAILURE", "EKS_POD_PENDING"}:
            print(f"Waiting for EKS pod diagnostic signal for job run {job_run_id}…")
            found_signal = wait_for_eks_pod_signal(
                namespace=namespace,
                job_run_id=job_run_id,
                expected_category=expected_category,
                timeout=args.wait_timeout,
                poll_interval=args.poll_interval,
            )
            if found_signal:
                print(f"  EKS pod diagnostic signal observed: {expected_category}")
                context = export_context(repo_root, context_file, exported_file)
            else:
                print("  Warning: EKS pod diagnostic signal was not observed before timeout.")

        if expected_category not in {"EKS_IMAGE_PULL_FAILURE", "EKS_POD_PENDING"}:
            print(f"Waiting for EMR on EKS job run {job_run_id} to complete…")
            try:
                final_state = wait_for_eks_job(
                    virtual_cluster_id,
                    job_run_id,
                    region,
                    timeout=args.wait_timeout,
                    poll_interval=args.poll_interval,
                )
                print(f"  EMR on EKS job state: {final_state}")
                context = export_context(repo_root, context_file, exported_file)
            except (TimeoutError, RuntimeError) as exc:
                print(f"  Warning: {exc}. Proceeding with current context.")
    elif (
        expected_outcome != "running"
        and runtime == "emr_ec2"
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

    if expected_outcome != "running" and not args.no_log_wait and runtime == "emr_ec2":
        print("Waiting for EMR logs in S3…")
        context = wait_for_emr_s3_logs(
            repo_root=repo_root,
            context_file=context_file,
            exported_file=exported_file,
            context=context,
            expected_outcome=expected_outcome,
            timeout=args.log_wait_timeout,
            poll_interval=args.log_poll_interval,
        )
    elif expected_outcome != "running" and not args.no_log_wait and runtime == "emr_serverless":
        print("Waiting for EMR Serverless logs…")
        context = wait_for_serverless_logs(
            repo_root=repo_root,
            context_file=context_file,
            exported_file=exported_file,
            context=context,
            expected_outcome=expected_outcome,
            timeout=args.log_wait_timeout,
            poll_interval=args.log_poll_interval,
        )
    elif expected_outcome != "running" and not args.no_log_wait and runtime == "emr_eks":
        print("Skipping EC2 step-log wait for EMR on EKS runtime.")

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
    if mcp_args.get("runtime") == "emr_serverless":
        print(f"  Starting investigation (job_run={mcp_args['target'].get('job_run_id')})…")
    elif mcp_args.get("runtime") == "emr_eks":
        print(f"  Starting investigation (job_run={mcp_args['target'].get('job_run_id')})…")
    else:
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
