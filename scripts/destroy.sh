#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../infra/terraform"

echo "About to destroy Harrier demo infrastructure."
echo
terraform state list || true
echo
read -r -p "Type destroy-harrier-demo to continue: " confirmation

if [[ "$confirmation" != "destroy-harrier-demo" ]]; then
  echo "Destroy cancelled."
  exit 1
fi

terraform destroy
