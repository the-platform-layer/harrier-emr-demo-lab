from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from validation.devops_agent_oom_comparison import (
    RUNTIMES,
    harrier_prompt,
    native_prompt,
    write_artifacts,
)


def _context(runtime: str) -> dict:
    base = {
        "runtime": runtime,
        "region": "ap-southeast-2",
        "job_state": "failed",
        "time_window": {
            "start": "2026-06-01T00:00:00Z",
            "end": "2026-06-01T00:30:00Z",
        },
        "log_uri": "s3://harrier-demo-logs/example/",
        "input_path": "s3://harrier-demo-raw/input.csv",
        "output_path": "s3://harrier-demo-processed/output/",
    }
    if runtime == "emr_ec2":
        base.update(
            {
                "cluster_id": "j-ABC123",
                "step_id": "s-ABC123",
                "application_id": "application_1_0001",
                "deploy_mode": "cluster",
            }
        )
    elif runtime == "emr_serverless":
        base.update(
            {
                "serverless_application_id": "00fabc123",
                "job_run_id": "00gabc123",
                "cloudwatch_log_group": "/harrier-demo/emr-serverless",
                "cloudwatch_log_stream_prefix": "harrier-demo/example",
            }
        )
    else:
        base.update(
            {
                "virtual_cluster_id": "vc-abc123",
                "job_run_id": "000000abc123",
                "eks_cluster_name": "harrier-demo-eks",
                "namespace": "harrier-emr-jobs",
                "cloudwatch_log_group": "/harrier-demo/emr-eks",
                "cloudwatch_log_stream_prefix": "harrier-demo/example",
            }
        )
    return base


class DevOpsAgentOOMComparisonTests(unittest.TestCase):
    def test_native_prompt_excludes_harrier_and_expected_category(self) -> None:
        prompt = native_prompt(_context("emr_ec2"))

        self.assertIn("native-baseline AWS DevOps Agent Space", prompt)
        self.assertIn("do not call any tool whose name starts with harrier", prompt)
        self.assertIn("j-ABC123", prompt)
        self.assertNotIn("EXECUTOR_OOM", prompt)
        self.assertNotIn("executor_oom", prompt)

    def test_harrier_prompts_include_runtime_aware_targets(self) -> None:
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                prompt = harrier_prompt(_context(runtime), "123456789012")

                self.assertIn("Use the Harrier EMR MCP tools first", prompt)
                self.assertIn("harrier_start_emr_investigation", prompt)
                self.assertIn('"account_id": "123456789012"', prompt)
                self.assertIn(f'"runtime": "{runtime}"', prompt)
                self.assertNotIn("EXECUTOR_OOM", prompt)

    def test_write_artifacts_creates_prompts_scorecard_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            comparison_dir = Path(tmp)
            contexts = {runtime: _context(runtime) for runtime in RUNTIMES}

            write_artifacts(comparison_dir, contexts, account_id="123456789012")

            prompts = (comparison_dir / "prompts.md").read_text(encoding="utf-8")
            scorecard = (comparison_dir / "scorecard.md").read_text(encoding="utf-8")
            metadata = json.loads((comparison_dir / "metadata.json").read_text(encoding="utf-8"))

            self.assertIn("Native DevOps Agent Prompt", prompts)
            self.assertIn("DevOps Agent With Harrier MCP Prompt", prompts)
            self.assertIn("Identifies executor OOM", scorecard)
            self.assertIn("Native EC2", scorecard)
            self.assertIn("Harrier EKS", scorecard)
            self.assertEqual(metadata["comparison"], "devops_agent_oom")
            self.assertEqual(metadata["scenario"], "executor_oom")

    def test_docs_and_shell_script_are_wired(self) -> None:
        script = ROOT / "scripts" / "run_devops_agent_oom_comparison.sh"
        docs = (ROOT / "docs" / "devops-agent-oom-comparison.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        subprocess.run(["bash", "-n", str(script)], check=True)
        self.assertIn("Native DevOps Agent", docs)
        self.assertIn("Harrier MCP", docs)
        self.assertIn("executor_oom", docs)
        self.assertIn("devops-agent-oom-comparison.md", readme)
        self.assertIn("compare-oom", makefile)


if __name__ == "__main__":
    unittest.main()
