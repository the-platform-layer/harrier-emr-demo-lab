from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SLICE14 = {
    "data_skew": ("DATA_SKEW", "cluster", "data skew"),
    "shuffle_spill": ("SHUFFLE_SPILL", "cluster", "shuffle spill"),
    "kms_access_denied": ("KMS_ACCESS_DENIED", "cluster", "kms:Decrypt"),
    "hdfs_full": ("HDFS_FULL", "cluster", "No space left on device"),
    "db_connection_failure": ("DB_CONNECTION_FAILURE", "client", "PSQLException JDBC connection refused"),
    "db_lock_timeout": ("DB_LOCK_TIMEOUT", "client", "lock timeout"),
    "db_partition_hotspot": ("DB_PARTITION_HOTSPOT", "cluster", "partition hotspot"),
    "db_large_join_spill": ("DB_LARGE_JOIN_SPILL", "cluster", "hash join spill"),
    "db_bad_sql_plan": ("DB_BAD_SQL_PLAN", "cluster", "sequential scan"),
    "livy_session_failure": ("LIVY_SESSION_FAILURE", "client", "Livy session failed"),
    "long_running_data_delay": ("RUNNING_JOB_DATA_DELAY", "cluster", "long_running_data_delay"),
    "long_running_resource_delay": ("RUNNING_JOB_RESOURCE_DELAY", "cluster", "long_running_resource_delay"),
    "long_running_db_delay": ("RUNNING_JOB_DB_DELAY", "cluster", "long_running_db_delay"),
}


class Slice14ScenarioTests(unittest.TestCase):
    def test_jobs_or_simulators_are_implemented(self) -> None:
        for scenario, (_, _, signal) in SLICE14.items():
            with self.subTest(scenario=scenario):
                job_path = ROOT / "spark-jobs" / scenario / "job.py"
                content = job_path.read_text(encoding="utf-8")

                self.assertNotIn("Placeholder", content)
                self.assertIn(signal, content)

    def test_expected_findings_have_validation_shape(self) -> None:
        for scenario, (category, _, _) in SLICE14.items():
            with self.subTest(scenario=scenario):
                data = json.loads(
                    (ROOT / "expected-findings" / f"{scenario}.json").read_text(encoding="utf-8")
                )

                self.assertEqual(data["scenario"], scenario)
                self.assertEqual(data["expected_root_cause_category"], category)
                self.assertIn(data["expected_outcome"], {"failed", "running"})
                self.assertGreaterEqual(len(data["expected_evidence"]), 2)
                self.assertGreaterEqual(len(data["expected_recommendations"]), 1)

    def test_scenario_configs_align_with_expected_findings(self) -> None:
        for scenario, (category, deploy_mode, _) in SLICE14.items():
            with self.subTest(scenario=scenario):
                config = json.loads(
                    (ROOT / "scenario-configs" / f"{scenario}.json").read_text(encoding="utf-8")
                )

                self.assertEqual(config["scenario"], scenario)
                self.assertEqual(config["slice"], 14)
                self.assertEqual(config["intended_deploy_mode"], deploy_mode)
                self.assertEqual(config["expected_root_cause_category"], category)
                self.assertTrue((ROOT / config["job"]).is_file())

    def test_runner_and_submitter_include_slice14_scenarios(self) -> None:
        runner = (ROOT / "scripts" / "run_scenario.sh").read_text(encoding="utf-8")
        submitter = (ROOT / "scripts" / "submit_step.sh").read_text(encoding="utf-8")

        for scenario in SLICE14:
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, runner)
                self.assertIn(f"{scenario})", submitter)

    def test_lock_simulator_is_safe_and_documented(self) -> None:
        simulator = (ROOT / "db" / "lock_simulator.py").read_text(encoding="utf-8")

        self.assertNotIn("Placeholder", simulator)
        self.assertIn("does not connect to a database", simulator)
        self.assertIn("lock timeout", simulator)


if __name__ == "__main__":
    unittest.main()
