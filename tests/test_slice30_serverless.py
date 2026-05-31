"""Static tests for Slice 30 EMR Serverless demo lab support."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVERLESS_SCENARIOS = {
    "happy_path": "UNKNOWN",
    "executor_oom": "EXECUTOR_OOM",
    "missing_dependency": "DEPENDENCY_MISSING",
    "s3_path_missing": "S3_PATH_MISSING",
    "bad_input_data": "BAD_INPUT_DATA",
}


class Slice30ServerlessTests(unittest.TestCase):
    def test_terraform_declares_serverless_application_and_outputs(self) -> None:
        serverless_tf = (ROOT / "infra" / "terraform" / "emr-serverless.tf").read_text(
            encoding="utf-8"
        )
        outputs_tf = (ROOT / "infra" / "terraform" / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_emrserverless_application" "demo"', serverless_tf)
        self.assertIn('type          = "spark"', serverless_tf)
        self.assertIn("emr-serverless.amazonaws.com", serverless_tf)
        self.assertIn('resource "aws_cloudwatch_log_group" "emr_serverless"', serverless_tf)
        self.assertIn("emr_serverless_application_id", outputs_tf)
        self.assertIn("emr_serverless_job_role_arn", outputs_tf)
        self.assertIn("emr_serverless_log_uri", outputs_tf)

    def test_submitter_and_runner_wire_supported_scenarios(self) -> None:
        submitter = (ROOT / "scripts" / "submit_serverless_job.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "run_scenario.sh").read_text(encoding="utf-8")

        self.assertIn("aws emr-serverless start-job-run", submitter)
        self.assertIn('"runtime": "emr_serverless"', submitter)
        self.assertIn("cloudWatchLoggingConfiguration", submitter)
        self.assertIn("s3MonitoringConfiguration", submitter)
        self.assertIn("RUNTIME=\"emr_serverless\"", runner)

        for scenario in SERVERLESS_SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertIn(f"{scenario})", submitter)
                self.assertIn(scenario, runner)

    def test_serverless_scenario_configs_point_to_jobs_and_expected_findings(self) -> None:
        for scenario, expected_category in SERVERLESS_SCENARIOS.items():
            with self.subTest(scenario=scenario):
                path = ROOT / "scenario-configs" / "emr_serverless" / f"{scenario}.json"
                config = json.loads(path.read_text(encoding="utf-8"))

                self.assertEqual(config["scenario"], scenario)
                self.assertEqual(config["runtime"], "emr_serverless")
                self.assertEqual(config["slice"], 30)
                self.assertEqual(config["expected_root_cause_category"], expected_category)
                self.assertTrue((ROOT / config["job"]).is_file())
                self.assertTrue((ROOT / config["expected_findings"]).is_file())

    def test_shell_scripts_parse(self) -> None:
        for script in (
            ROOT / "scripts" / "run_scenario.sh",
            ROOT / "scripts" / "submit_serverless_job.sh",
            ROOT / "scripts" / "export_investigation_context.sh",
            ROOT / "scripts" / "cleanup_scenario.sh",
        ):
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], check=False)
                self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
