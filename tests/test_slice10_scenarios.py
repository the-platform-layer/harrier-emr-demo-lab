from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BATCH1 = {
    "executor_oom": {
        "category": "EXECUTOR_OOM",
        "deploy_mode": "cluster",
        "signal": "java.lang.OutOfMemoryError",
    },
    "driver_oom": {
        "category": "DRIVER_OOM",
        "deploy_mode": "client",
        "signal": "driver java.lang.OutOfMemoryError",
    },
    "missing_dependency": {
        "category": "DEPENDENCY_MISSING",
        "deploy_mode": "client",
        "signal": "ModuleNotFoundError",
    },
    "s3_access_denied": {
        "category": "S3_ACCESS_DENIED",
        "deploy_mode": "cluster",
        "signal": "AccessDenied while reading",
    },
    "bad_input_data": {
        "category": "BAD_INPUT_DATA",
        "deploy_mode": "cluster",
        "signal": "CSV malformed",
    },
}


class Slice10ScenarioTests(unittest.TestCase):
    def test_jobs_are_implemented_with_classifier_signals(self) -> None:
        for scenario, expected in BATCH1.items():
            with self.subTest(scenario=scenario):
                job_path = ROOT / "spark-jobs" / scenario / "job.py"
                content = job_path.read_text(encoding="utf-8")

                self.assertNotIn("Placeholder", content)
                self.assertIn("SparkSession", content)
                self.assertIn(expected["signal"], content)

    def test_expected_findings_have_validation_shape(self) -> None:
        for scenario, expected in BATCH1.items():
            with self.subTest(scenario=scenario):
                data = json.loads(
                    (ROOT / "expected-findings" / f"{scenario}.json").read_text(encoding="utf-8")
                )

                self.assertEqual(data["scenario"], scenario)
                self.assertEqual(data["expected_outcome"], "failed")
                self.assertEqual(data["expected_root_cause_category"], expected["category"])
                self.assertGreaterEqual(len(data["expected_evidence"]), 2)
                self.assertGreaterEqual(len(data["expected_recommendations"]), 1)

    def test_scenario_configs_align_with_expected_findings(self) -> None:
        for scenario, expected in BATCH1.items():
            with self.subTest(scenario=scenario):
                config = json.loads(
                    (ROOT / "scenario-configs" / f"{scenario}.json").read_text(encoding="utf-8")
                )

                self.assertEqual(config["scenario"], scenario)
                self.assertEqual(config["slice"], 10)
                self.assertEqual(config["intended_deploy_mode"], expected["deploy_mode"])
                self.assertEqual(config["expected_root_cause_category"], expected["category"])
                self.assertTrue((ROOT / config["job"]).is_file())

    def test_runner_and_submitter_include_batch1_scenarios(self) -> None:
        runner = (ROOT / "scripts" / "run_scenario.sh").read_text(encoding="utf-8")
        submitter = (ROOT / "scripts" / "submit_step.sh").read_text(encoding="utf-8")

        for scenario in BATCH1:
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, runner)
                self.assertIn(f"{scenario})", submitter)


if __name__ == "__main__":
    unittest.main()
