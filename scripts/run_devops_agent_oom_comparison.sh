#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"

exec "$python_bin" "$repo_root/validation/devops_agent_oom_comparison.py" "$@"
