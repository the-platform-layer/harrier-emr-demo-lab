#!/usr/bin/env python3
"""Prepare a DevOps Agent OOM comparison across EMR runtimes.

The comparison has two lanes:
  * native AWS DevOps Agent without Harrier tools allowlisted
  * AWS DevOps Agent with Harrier MCP read-only tools allowlisted

This module can submit the demo OOM scenarios, wait for terminal evidence, export
runtime-aware context, and generate prompt and scorecard artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from validation.validate import (
    export_context,
    wait_for_eks_job,
    wait_for_emr_s3_logs,
    wait_for_serverless_job,
    wait_for_serverless_logs,
    wait_for_step,
)

SCENARIO = "executor_oom"
RUNTIMES = ("emr_ec2", "emr_serverless", "emr_eks")
RUNTIME_LABELS = {
    "emr_ec2": "EMR on EC2",
    "emr_serverless": "EMR Serverless",
    "emr_eks": "EMR on EKS",
}
RUNTIME_CONTEXT_ENV = {
    "emr_ec2": "EMR_EC2_CONTEXT_FILE",
    "emr_serverless": "EMR_SERVERLESS_CONTEXT_FILE",
    "emr_eks": "EMR_EKS_CONTEXT_FILE",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare native-vs-Harrier DevOps Agent OOM comparison artifacts",
    )
    parser.add_argument(
        "--comparison-dir",
        default="",
        help="Output directory. Defaults to .harrier-demo/comparisons/oom-<timestamp>.",
    )
    parser.add_argument(
        "--account-id",
        default=os.environ.get("AWS_ACCOUNT_ID", ""),
        help="12-digit AWS account ID used in prompts and Harrier calls.",
    )
    parser.add_argument(
        "--runtimes",
        default=",".join(RUNTIMES),
        help="Comma-separated runtimes to include. Default: emr_ec2,emr_serverless,emr_eks.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        default=os.environ.get("SKIP_SCENARIO_RUN", "0") == "1",
        help="Use existing context files instead of submitting new jobs.",
    )
    parser.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="RUNTIME=PATH",
        help="Existing context file for a runtime. May be repeated.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=int(os.environ.get("WAIT_TIMEOUT", "900")),
        help="Seconds to wait for terminal job state.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("POLL_INTERVAL", "20")),
        help="Seconds between state polls.",
    )
    parser.add_argument(
        "--log-wait-timeout",
        type=int,
        default=int(os.environ.get("LOG_WAIT_TIMEOUT", "420")),
        help="Seconds to wait for log visibility.",
    )
    parser.add_argument(
        "--log-poll-interval",
        type=int,
        default=int(os.environ.get("LOG_POLL_INTERVAL", "30")),
        help="Seconds between log visibility polls.",
    )
    parser.add_argument(
        "--no-log-wait",
        action="store_true",
        default=os.environ.get("NO_LOG_WAIT", "0") == "1",
        help="Skip log visibility waits.",
    )
    return parser.parse_args(argv)


def _comparison_id() -> str:
    return "oom-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _default_comparison_dir(repo_root: Path) -> Path:
    return repo_root / ".harrier-demo" / "comparisons" / _comparison_id()


def _parse_runtime_list(raw: str) -> list[str]:
    runtimes = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [item for item in runtimes if item not in RUNTIMES]
    if unknown:
        raise ValueError(f"Unsupported runtime(s): {', '.join(unknown)}")
    return runtimes


def _parse_context_args(items: list[str]) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"--context must be RUNTIME=PATH, got {item!r}")
        runtime, raw_path = item.split("=", 1)
        runtime = runtime.strip()
        if runtime not in RUNTIMES:
            raise ValueError(f"Unsupported context runtime: {runtime}")
        mapping[runtime] = Path(raw_path).expanduser()
    for runtime, env_name in RUNTIME_CONTEXT_ENV.items():
        if runtime not in mapping and os.environ.get(env_name):
            mapping[runtime] = Path(os.environ[env_name]).expanduser()
    return mapping


def _runtime_context_file(comparison_dir: Path, runtime: str) -> Path:
    return comparison_dir / "contexts" / f"{runtime}-{SCENARIO}.json"


def _runtime_exported_file(comparison_dir: Path, runtime: str) -> Path:
    return comparison_dir / "contexts" / f"{runtime}-{SCENARIO}-exported.json"


def _runtime_run_id(comparison_dir: Path, runtime: str) -> str:
    return f"{comparison_dir.name}-{runtime}"


def _run_single_runtime(
    repo_root: Path,
    comparison_dir: Path,
    runtime: str,
    existing_contexts: dict[str, Path],
    *,
    skip_run: bool,
    wait_timeout: int,
    poll_interval: int,
    log_wait_timeout: int,
    log_poll_interval: int,
    no_log_wait: bool,
) -> dict[str, Any]:
    context_file = existing_contexts.get(runtime) or _runtime_context_file(comparison_dir, runtime)
    exported_file = _runtime_exported_file(comparison_dir, runtime)
    context_file.parent.mkdir(parents=True, exist_ok=True)
    exported_file.parent.mkdir(parents=True, exist_ok=True)

    if skip_run:
        if not context_file.is_file():
            raise FileNotFoundError(
                f"Context file for {runtime} not found: {context_file}. "
                f"Pass --context {runtime}=PATH or set {RUNTIME_CONTEXT_ENV[runtime]}."
            )
        print(f"[{runtime}] Using existing context: {context_file}")
    else:
        print(f"[{runtime}] Submitting {SCENARIO}")
        env = os.environ.copy()
        env["RUNTIME"] = runtime
        env["RUN_ID"] = _runtime_run_id(comparison_dir, runtime)
        env["CONTEXT_FILE"] = str(context_file)
        result = subprocess.run(
            ["bash", str(repo_root / "scripts" / "run_scenario.sh"), SCENARIO],
            cwd=repo_root,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"run_scenario.sh exited {result.returncode} for {runtime}")

    print(f"[{runtime}] Exporting investigation context")
    context = export_context(repo_root, context_file, exported_file)

    if not skip_run:
        context = _wait_for_terminal_context(
            repo_root,
            runtime,
            context_file,
            exported_file,
            context,
            wait_timeout=wait_timeout,
            poll_interval=poll_interval,
        )

    if not no_log_wait:
        context = _wait_for_logs(
            repo_root,
            runtime,
            context_file,
            exported_file,
            context,
            log_wait_timeout=log_wait_timeout,
            log_poll_interval=log_poll_interval,
        )

    return context


def _wait_for_terminal_context(
    repo_root: Path,
    runtime: str,
    context_file: Path,
    exported_file: Path,
    context: dict[str, Any],
    *,
    wait_timeout: int,
    poll_interval: int,
) -> dict[str, Any]:
    region = context.get("region", "")

    if runtime == "emr_ec2":
        cluster_id = context.get("cluster_id", "")
        step_id = context.get("step_id", "")
        if cluster_id and step_id and region:
            print(f"[{runtime}] Waiting for step {step_id} to reach a terminal state")
            try:
                state = wait_for_step(
                    cluster_id,
                    step_id,
                    region,
                    timeout=wait_timeout,
                    poll_interval=poll_interval,
                )
                print(f"[{runtime}] Step state: {state}")
                return export_context(repo_root, context_file, exported_file)
            except (RuntimeError, TimeoutError) as exc:
                print(f"[{runtime}] Warning: {exc}")

    if runtime == "emr_serverless":
        application_id = context.get("serverless_application_id", "")
        job_run_id = context.get("job_run_id", "")
        if application_id and job_run_id and region:
            print(f"[{runtime}] Waiting for job run {job_run_id} to reach a terminal state")
            try:
                state = wait_for_serverless_job(
                    application_id,
                    job_run_id,
                    region,
                    timeout=wait_timeout,
                    poll_interval=poll_interval,
                )
                print(f"[{runtime}] Job state: {state}")
                return export_context(repo_root, context_file, exported_file)
            except (RuntimeError, TimeoutError) as exc:
                print(f"[{runtime}] Warning: {exc}")

    if runtime == "emr_eks":
        virtual_cluster_id = context.get("virtual_cluster_id", "")
        job_run_id = context.get("job_run_id", "")
        if virtual_cluster_id and job_run_id and region:
            print(f"[{runtime}] Waiting for job run {job_run_id} to reach a terminal state")
            try:
                state = wait_for_eks_job(
                    virtual_cluster_id,
                    job_run_id,
                    region,
                    timeout=wait_timeout,
                    poll_interval=poll_interval,
                )
                print(f"[{runtime}] Job state: {state}")
                return export_context(repo_root, context_file, exported_file)
            except (RuntimeError, TimeoutError) as exc:
                print(f"[{runtime}] Warning: {exc}")

    return context


def _wait_for_logs(
    repo_root: Path,
    runtime: str,
    context_file: Path,
    exported_file: Path,
    context: dict[str, Any],
    *,
    log_wait_timeout: int,
    log_poll_interval: int,
) -> dict[str, Any]:
    if runtime == "emr_ec2":
        print(f"[{runtime}] Waiting for EMR step and YARN logs")
        return wait_for_emr_s3_logs(
            repo_root=repo_root,
            context_file=context_file,
            exported_file=exported_file,
            context=context,
            expected_outcome="failed",
            timeout=log_wait_timeout,
            poll_interval=log_poll_interval,
        )
    if runtime == "emr_serverless":
        print(f"[{runtime}] Waiting for EMR Serverless logs")
        return wait_for_serverless_logs(
            repo_root=repo_root,
            context_file=context_file,
            exported_file=exported_file,
            context=context,
            expected_outcome="failed",
            timeout=log_wait_timeout,
            poll_interval=log_poll_interval,
        )
    print(f"[{runtime}] EKS log wait is handled by DevOps Agent and Harrier collectors")
    return context


def _time_window(context: dict[str, Any]) -> str:
    window = context.get("time_window") or {}
    start = window.get("start") or "(unknown start)"
    end = window.get("end") or "(unknown end)"
    return f"{start} to {end}"


def _context_summary(context: dict[str, Any]) -> list[str]:
    runtime = context.get("runtime", "emr_ec2")
    region = context.get("region", "")
    lines = [f"- Runtime: {RUNTIME_LABELS.get(runtime, runtime)}", f"- Region: {region}"]

    if runtime == "emr_serverless":
        lines.extend(
            [
                f"- EMR Serverless application ID: {context.get('serverless_application_id', '')}",
                f"- Job run ID: {context.get('job_run_id', '')}",
            ]
        )
    elif runtime == "emr_eks":
        lines.extend(
            [
                f"- EMR on EKS virtual cluster ID: {context.get('virtual_cluster_id', '')}",
                f"- Job run ID: {context.get('job_run_id', '')}",
                f"- EKS cluster name: {context.get('eks_cluster_name', '')}",
                f"- Namespace: {context.get('namespace', '')}",
            ]
        )
    else:
        lines.extend(
            [
                f"- EMR cluster ID: {context.get('cluster_id', '')}",
                f"- EMR step ID: {context.get('step_id', '')}",
                f"- YARN application ID: {context.get('application_id', '')}",
                f"- Spark deploy mode: {context.get('deploy_mode', 'unknown')}",
            ]
        )

    lines.extend(
        [
            f"- Investigation time window: {_time_window(context)}",
            f"- S3 log URI: {context.get('log_uri', '')}",
        ]
    )
    if context.get("cloudwatch_log_group"):
        lines.append(f"- CloudWatch log group: {context.get('cloudwatch_log_group')}")
    if context.get("cloudwatch_log_stream_prefix"):
        lines.append(
            f"- CloudWatch log stream prefix: {context.get('cloudwatch_log_stream_prefix')}"
        )
    if context.get("input_path"):
        lines.append(f"- Input path: {context.get('input_path')}")
    if context.get("output_path"):
        lines.append(f"- Output path: {context.get('output_path')}")
    return lines


def native_prompt(context: dict[str, Any]) -> str:
    label = RUNTIME_LABELS.get(context.get("runtime", "emr_ec2"), context.get("runtime", ""))
    details = "\n".join(_context_summary(context))
    return f"""You are in the native-baseline AWS DevOps Agent Space.

Investigate this failed {label} Spark job using AWS DevOps Agent native capabilities only.
Do not use custom MCP servers and do not call any tool whose name starts with harrier.
Use AWS, CloudWatch, topology, deployment context, and logs that the native Agent Space can access.

Context:

{details}

Return a concise operator-facing report with these sections:

1. Initial diagnosis
2. Runtime-specific check map
3. Evidence used
4. Important gaps or inconclusive checks
5. Recommended next actions

Do not mutate AWS resources. Do not propose a final RCA unless the evidence is conclusive.
"""


def harrier_prompt(context: dict[str, Any], account_id: str) -> str:
    runtime = context.get("runtime", "emr_ec2")
    label = RUNTIME_LABELS.get(runtime, runtime)
    details = "\n".join(_context_summary(context))
    target_instruction = _harrier_target_instruction(context, account_id)
    return f"""You are in the Harrier-enabled AWS DevOps Agent Space.

Use the Harrier EMR MCP tools first to investigate this failed {label} Spark job.
Prefer the Harrier human Initial Diagnosis Report when presenting the answer.

Context:

{details}

Harrier tool call guidance:

{target_instruction}

Return a concise operator-facing report with these sections:

1. Initial diagnosis
2. Runtime-specific check map
3. Evidence used
4. Important gaps or inconclusive checks
5. Recommended next actions

Include Harrier confidence, log excerpts, and any NOT CHECKED or INCONCLUSIVE checks.
Use dry-run remediation only; do not mutate AWS resources.
"""


def _harrier_target_instruction(context: dict[str, Any], account_id: str) -> str:
    runtime = context.get("runtime", "emr_ec2")
    base = {
        "account_id": account_id or "<AWS_ACCOUNT_ID>",
        "region": context.get("region", ""),
        "runtime": runtime,
        "job_state": context.get("job_state", "failed"),
    }
    if context.get("time_window"):
        base["time_window"] = context["time_window"]

    if runtime == "emr_serverless":
        base["target"] = {
            "serverless_application_id": context.get("serverless_application_id", ""),
            "job_run_id": context.get("job_run_id", ""),
        }
    elif runtime == "emr_eks":
        base["target"] = {
            "virtual_cluster_id": context.get("virtual_cluster_id", ""),
            "job_run_id": context.get("job_run_id", ""),
            "eks_cluster_name": context.get("eks_cluster_name", ""),
            "namespace": context.get("namespace", ""),
        }
    else:
        base["target"] = {
            "cluster_id": context.get("cluster_id", ""),
            "step_id": context.get("step_id", ""),
        }
        if context.get("application_id"):
            base["target"]["yarn_application_id"] = context["application_id"]
        base["deploy_mode"] = context.get("deploy_mode", "unknown")

    encoded = json.dumps(base, indent=2, sort_keys=True)
    return (
        "Call harrier_start_emr_investigation with this runtime-aware target, then "
        "call harrier_get_investigation_report if the first response does not include "
        "the full human report:\n\n"
        f"```json\n{encoded}\n```"
    )


def write_artifacts(
    comparison_dir: Path,
    contexts: dict[str, dict[str, Any]],
    *,
    account_id: str,
) -> None:
    comparison_dir.mkdir(parents=True, exist_ok=True)
    (comparison_dir / "responses").mkdir(parents=True, exist_ok=True)
    _write_prompts(comparison_dir / "prompts.md", contexts, account_id=account_id)
    _write_scorecard(comparison_dir / "scorecard.md", contexts)
    _write_metadata(comparison_dir / "metadata.json", contexts, account_id=account_id)


def _write_prompts(path: Path, contexts: dict[str, dict[str, Any]], *, account_id: str) -> None:
    parts = [
        "# DevOps Agent OOM Comparison Prompts",
        "",
        "Use the native prompts in an Agent Space with Harrier disabled.",
        "Use the Harrier prompts in an Agent Space with Harrier MCP read-only tools allowlisted.",
        "",
    ]
    for runtime in RUNTIMES:
        if runtime not in contexts:
            continue
        label = RUNTIME_LABELS[runtime]
        parts.extend(
            [
                f"## {label}",
                "",
                "### Native DevOps Agent Prompt",
                "",
                "```text",
                native_prompt(contexts[runtime]).strip(),
                "```",
                "",
                "### DevOps Agent With Harrier MCP Prompt",
                "",
                "```text",
                harrier_prompt(contexts[runtime], account_id).strip(),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(parts), encoding="utf-8")


def _write_scorecard(path: Path, contexts: dict[str, dict[str, Any]]) -> None:
    runtime_columns = []
    for runtime in RUNTIMES:
        if runtime in contexts:
            short = {
                "emr_ec2": "EC2",
                "emr_serverless": "Serverless",
                "emr_eks": "EKS",
            }[runtime]
            runtime_columns.extend([f"Native {short}", f"Harrier {short}"])

    header = "| Criterion | Why It Matters | " + " | ".join(runtime_columns) + " |"
    divider = "| --- | --- | " + " | ".join("---" for _ in runtime_columns) + " |"
    blank = " | ".join("" for _ in runtime_columns)
    criteria = [
        (
            "Identifies executor OOM",
            "The investigation should classify executor-side memory pressure rather than generic job failure.",
        ),
        (
            "Distinguishes driver vs executor",
            "A driver OOM fix and executor OOM fix are different.",
        ),
        (
            "Uses runtime-specific identifiers",
            "The answer should cite the right cluster, step, job run, virtual cluster, or namespace.",
        ),
        (
            "Cites concrete log evidence",
            "The answer should quote bounded log excerpts or exact log signals, not only summarize.",
        ),
        (
            "Explains missing or inconclusive evidence",
            "The answer should say what was not checked and what would confirm it.",
        ),
        (
            "Gives runtime-specific recommendations",
            "EC2/YARN, Serverless worker sizing, and EKS pod resources need different remediation hints.",
        ),
        (
            "Avoids unsafe mutations",
            "The test should not resize clusters, change IAM, or edit code without approval.",
        ),
        (
            "Overall operator usefulness",
            "The answer should be readable enough for an on-call engineer to act on quickly.",
        ),
    ]

    lines = [
        "# DevOps Agent OOM Comparison Scorecard",
        "",
        "Score each cell from `0` to `3`.",
        "",
        "- `0`: missing or wrong",
        "- `1`: mentioned but vague",
        "- `2`: mostly correct with usable evidence",
        "- `3`: clear, evidence-backed, and actionable",
        "",
        header,
        divider,
    ]
    for criterion, why in criteria:
        lines.append(f"| {criterion} | {why} | {blank} |")

    lines.extend(
        [
            "",
            "## Response Files",
            "",
            "Paste or save Agent responses under:",
            "",
        ]
    )
    for runtime in contexts:
        lines.append(f"- `responses/native-{runtime}.md`")
        lines.append(f"- `responses/harrier-{runtime}.md`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_metadata(path: Path, contexts: dict[str, dict[str, Any]], *, account_id: str) -> None:
    metadata = {
        "comparison": "devops_agent_oom",
        "scenario": SCENARIO,
        "account_id": account_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtimes": {
            runtime: {
                "label": RUNTIME_LABELS[runtime],
                "region": context.get("region"),
                "time_window": context.get("time_window"),
                "job_state": context.get("job_state"),
            }
            for runtime, context in contexts.items()
        },
    }
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = _REPO_ROOT

    try:
        runtimes = _parse_runtime_list(args.runtimes)
        existing_contexts = _parse_context_args(args.context)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    comparison_dir = (
        Path(args.comparison_dir).expanduser()
        if args.comparison_dir
        else _default_comparison_dir(repo_root)
    )
    if not comparison_dir.is_absolute():
        comparison_dir = repo_root / comparison_dir

    contexts: dict[str, dict[str, Any]] = {}
    comparison_dir.mkdir(parents=True, exist_ok=True)

    for runtime in runtimes:
        try:
            contexts[runtime] = _run_single_runtime(
                repo_root,
                comparison_dir,
                runtime,
                existing_contexts,
                skip_run=args.skip_run,
                wait_timeout=args.wait_timeout,
                poll_interval=args.poll_interval,
                log_wait_timeout=args.log_wait_timeout,
                log_poll_interval=args.log_poll_interval,
                no_log_wait=args.no_log_wait,
            )
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    write_artifacts(comparison_dir, contexts, account_id=args.account_id)
    print("")
    print(f"Comparison artifacts written to: {comparison_dir}")
    print(f"Prompts: {comparison_dir / 'prompts.md'}")
    print(f"Scorecard: {comparison_dir / 'scorecard.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
