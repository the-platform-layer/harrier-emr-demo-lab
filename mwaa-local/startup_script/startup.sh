#!/usr/bin/env bash
set -euo pipefail

mkdir -p /usr/local/airflow/harrier-demo-lab/.harrier-demo/runs
mkdir -p /usr/local/airflow/harrier-demo-lab/sample-data/generated
mkdir -p /usr/local/airflow/harrier-demo-lab/sample-data/large

echo "Harrier demo MWAA local runner startup complete."
