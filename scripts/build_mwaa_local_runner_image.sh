#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
source_dir="${MWAA_LOCAL_RUNNER_SOURCE_DIR:-$repo_root/.harrier-demo/aws-mwaa-local-runner}"
upstream_ref="${MWAA_LOCAL_RUNNER_REF:-v2.10.3}"
base_image="${MWAA_BASE_IMAGE:-amazon/mwaa-local:2_10_3}"
image_name="${IMAGE_NAME:-harrier-demo-mwaa-local}"
image_tag="${IMAGE_TAG:-$(git -C "$repo_root" rev-parse --short=8 HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)}"
repository_url="${MWAA_ECR_REPOSITORY_URL:-}"
docker_build_network="${DOCKER_BUILD_NETWORK:-host}"
push_image=false

while (($# > 0)); do
  case "$1" in
    --repository-url)
      repository_url="$2"
      shift 2
      ;;
    --tag)
      image_tag="$2"
      shift 2
      ;;
    --upstream-ref)
      upstream_ref="$2"
      shift 2
      ;;
    --push)
      push_image=true
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to build the MWAA local runner image." >&2
  exit 2
fi

mkdir -p "$(dirname "$source_dir")"
if [[ ! -d "$source_dir/.git" ]]; then
  git clone https://github.com/aws/aws-mwaa-local-runner.git "$source_dir"
fi

git -C "$source_dir" fetch --depth 1 origin "$upstream_ref"
git -C "$source_dir" checkout --detach FETCH_HEAD

if ! docker image inspect "$base_image" >/dev/null 2>&1; then
  echo "Building AWS MWAA local runner base image: $base_image"
  for attempt in 1 2 3; do
    if (
      cd "$source_dir"
      docker build --rm --compress \
        --network "$docker_build_network" \
        --tag "$base_image" \
        ./docker
    ); then
      break
    fi

    if [[ "$attempt" == 3 ]]; then
      echo "failed to build AWS MWAA local runner base image after $attempt attempts." >&2
      exit 1
    fi

    sleep_seconds=$((attempt * 20))
    echo "base image build failed; retrying in ${sleep_seconds}s (attempt $((attempt + 1))/3)."
    sleep "$sleep_seconds"
  done
fi

local_image="$image_name:$image_tag"
echo "Building Harrier MWAA local runner image: $local_image"
docker build \
  --platform linux/amd64 \
  --network "$docker_build_network" \
  --build-arg "MWAA_BASE_IMAGE=$base_image" \
  --file "$repo_root/mwaa-local/Dockerfile" \
  --tag "$local_image" \
  "$repo_root"

if [[ -n "$repository_url" ]]; then
  remote_image="$repository_url:$image_tag"
  docker tag "$local_image" "$remote_image"
  docker tag "$local_image" "$repository_url:latest"
  echo "Tagged remote image: $remote_image"

  if [[ "$push_image" == true ]]; then
    aws_region="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-2}}"
    aws ecr get-login-password --region "$aws_region" \
      | docker login --username AWS --password-stdin "${repository_url%/*}"
    docker push "$remote_image"
    docker push "$repository_url:latest"
    echo "Pushed image: $remote_image"
  fi
fi

echo "$image_tag"
