#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"
desired_count="${MWAA_DESIRED_COUNT:-1}"
image_tag="${IMAGE_TAG:-$(git -C "$repo_root" rev-parse --short=8 HEAD)}"
allowed_cidrs="${MWAA_WEB_ALLOWED_CIDRS:-}"

if [[ -z "$allowed_cidrs" ]]; then
  public_ip="$(curl -fsS https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)"
  if [[ -n "$public_ip" ]]; then
    allowed_cidrs="[\"$public_ip/32\"]"
  else
    allowed_cidrs="[\"0.0.0.0/0\"]"
  fi
fi

terraform -chdir="$tf_dir" init
terraform -chdir="$tf_dir" apply -target=aws_ecr_repository.mwaa_local_runner -auto-approve

repository_url="$(terraform -chdir="$tf_dir" output -raw mwaa_ecr_repository_url)"

"$repo_root/scripts/build_mwaa_local_runner_image.sh" \
  --repository-url "$repository_url" \
  --tag "$image_tag" \
  --push

terraform -chdir="$tf_dir" apply \
  -var "mwaa_image_tag=$image_tag" \
  -var "mwaa_desired_count=$desired_count" \
  -var "mwaa_web_allowed_cidrs=$allowed_cidrs" \
  -auto-approve

terraform -chdir="$tf_dir" output mwaa_airflow_url
