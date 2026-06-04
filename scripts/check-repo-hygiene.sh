#!/usr/bin/env bash
set -euo pipefail

denylist_regex='(^|/)\.DS_Store$|(^|/)\.env$|(^|/)\.terraform/|(^|/)[^/]*\.tfstate(\..*)?$|(^|/)terraform\.tfvars$|(^|/)\.harrier-demo/|(^|/)\.harrier-local/|^comparison-output/|(^|/)__pycache__/|(^|/)\.pytest_cache/|(^|/)\.ruff_cache/'

violations="$(
  git ls-files | grep -E "$denylist_regex" || true
)"

if [[ -n "$violations" ]]; then
  cat >&2 <<EOF
Tracked local/generated files were found:

$violations

Remove these files from git and keep them ignored. Public releases should not
include local state, generated scenario output, caches, credentials, or
Terraform state.
EOF
  exit 1
fi

echo "Repository hygiene check passed."
