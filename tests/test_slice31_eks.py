"""Static tests for Slice 31 EMR on EKS demo lab support."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EKS_SCENARIOS = {
    "happy_path": "UNKNOWN",
    "executor_oom": "EXECUTOR_OOM",
    "image_pull_failure": "EKS_IMAGE_PULL_FAILURE",
    "pod_pending_resource_pressure": "EKS_POD_PENDING",
    "s3_access_denied": "S3_ACCESS_DENIED",
}


class Slice31EksTests(unittest.TestCase):
    def test_terraform_declares_virtual_cluster_and_outputs(self) -> None:
        eks_tf = (ROOT / "infra" / "terraform" / "emr-eks.tf").read_text(encoding="utf-8")
        cluster_tf = (ROOT / "infra" / "terraform" / "eks-cluster.tf").read_text(encoding="utf-8")
        outputs_tf = (ROOT / "infra" / "terraform" / "outputs.tf").read_text(encoding="utf-8")
        variables_tf = (ROOT / "infra" / "terraform" / "variables.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_emrcontainers_virtual_cluster" "demo"', eks_tf)
        self.assertIn('type = "EKS"', eks_tf)
        self.assertIn("aws_cloudwatch_log_group\" \"emr_eks", eks_tf)
        self.assertIn('resource "aws_eks_cluster" "demo"', cluster_tf)
        self.assertIn('resource "aws_eks_node_group" "demo"', cluster_tf)
        self.assertIn('resource "aws_iam_openid_connect_provider" "eks"', cluster_tf)
        self.assertIn('resource "aws_iam_role" "emr_eks_job"', cluster_tf)
        self.assertIn("enable_emr_eks", variables_tf)
        self.assertIn("enable_demo_eks_cluster", variables_tf)
        self.assertIn("emr_eks_cluster_name", variables_tf)
        self.assertIn("emr_eks_job_role_arn", variables_tf)
        self.assertIn("emr_eks_virtual_cluster_id", outputs_tf)
        self.assertIn("demo_eks_node_group_name", outputs_tf)
        self.assertIn("emr_eks_log_uri", outputs_tf)

    def test_setup_submitter_and_runner_wire_supported_scenarios(self) -> None:
        setup = (ROOT / "scripts" / "setup_eks_virtual_cluster.sh").read_text(encoding="utf-8")
        submitter = (ROOT / "scripts" / "submit_eks_job.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "run_scenario.sh").read_text(encoding="utf-8")

        self.assertIn("aws eks update-kubeconfig", setup)
        self.assertIn("kind: RoleBinding", setup)
        self.assertIn("aws emr-containers update-role-trust-policy", setup)
        self.assertIn("aws emr-containers start-job-run", submitter)
        self.assertIn("sparkSubmitJobDriver", submitter)
        self.assertIn('"runtime": "emr_eks"', submitter)
        self.assertIn("cloudWatchMonitoringConfiguration", submitter)
        self.assertIn("s3MonitoringConfiguration", submitter)
        self.assertIn('short_scenario="${scenario//_/-}"', submitter)
        self.assertIn("RUNTIME=\"emr_eks\"", runner)

        for scenario in EKS_SCENARIOS:
            with self.subTest(scenario=scenario):
                self.assertIn(f"{scenario})", submitter)
                self.assertIn(scenario, runner)

    def test_eks_scenario_configs_point_to_jobs_and_expected_findings(self) -> None:
        for scenario, expected_category in EKS_SCENARIOS.items():
            with self.subTest(scenario=scenario):
                path = ROOT / "scenario-configs" / "emr_eks" / f"{scenario}.json"
                config = json.loads(path.read_text(encoding="utf-8"))

                self.assertEqual(config["scenario"], scenario)
                self.assertEqual(config["runtime"], "emr_eks")
                self.assertEqual(config["slice"], 31)
                self.assertEqual(config["expected_root_cause_category"], expected_category)
                self.assertTrue((ROOT / config["job"]).is_file())
                self.assertTrue((ROOT / config["expected_findings"]).is_file())

    def test_validation_harness_supports_eks_runtime(self) -> None:
        validator = (ROOT / "validation" / "validate.py").read_text(encoding="utf-8")
        exporter = (ROOT / "scripts" / "export_investigation_context.sh").read_text(encoding="utf-8")
        cleaner = (ROOT / "scripts" / "cleanup_scenario.sh").read_text(encoding="utf-8")

        self.assertIn("def wait_for_eks_job", validator)
        self.assertIn('"runtime": "emr_eks"', exporter)
        self.assertIn("emr-containers describe-job-run", exporter)
        self.assertIn("emr-containers cancel-job-run", cleaner)

    def test_docs_describe_eks_prerequisites_and_scenarios(self) -> None:
        docs = "\n".join(
            [
                (ROOT / "README.md").read_text(encoding="utf-8"),
                (ROOT / "docs" / "emr-on-eks-prerequisites.md").read_text(encoding="utf-8"),
                (ROOT / "docs" / "scenarios.md").read_text(encoding="utf-8"),
                (ROOT / "docs" / "validation-matrix.md").read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("EMR on EKS", docs)
        self.assertIn("EMR_EKS_CLUSTER_NAME", docs)
        self.assertIn("image_pull_failure", docs)
        self.assertIn("pod_pending_resource_pressure", docs)
        self.assertIn("runtime=emr_eks", docs)

    def test_shell_scripts_parse(self) -> None:
        for script in (
            ROOT / "scripts" / "run_scenario.sh",
            ROOT / "scripts" / "submit_eks_job.sh",
            ROOT / "scripts" / "setup_eks_virtual_cluster.sh",
            ROOT / "scripts" / "export_investigation_context.sh",
            ROOT / "scripts" / "cleanup_scenario.sh",
            ROOT / "scripts" / "validate_scenario.sh",
        ):
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], check=False)
                self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
