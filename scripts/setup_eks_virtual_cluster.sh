#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
tf_dir="$repo_root/infra/terraform"

tf_json="$(terraform -chdir="$tf_dir" output -json 2>/dev/null || printf '{}')"

tf_output() {
  TF_JSON="$tf_json" python3 - "$1" <<'PY'
import json
import os
import sys

name = sys.argv[1]
try:
    data = json.loads(os.environ.get("TF_JSON", "{}"))
except json.JSONDecodeError:
    data = {}

value = data.get(name, {}).get("value", "")
if value is None:
    value = ""
print(value)
PY
}

region="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(tf_output region)}}"
cluster_name="${EMR_EKS_CLUSTER_NAME:-${EKS_CLUSTER_NAME:-$(tf_output emr_eks_cluster_name)}}"
namespace="${EMR_EKS_NAMESPACE:-$(tf_output emr_eks_namespace)}"
job_role_arn="${EMR_EKS_JOB_ROLE_ARN:-$(tf_output emr_eks_job_role_arn)}"
job_role_name="${EMR_EKS_JOB_ROLE_NAME:-$(tf_output emr_eks_job_role_name)}"
job_role_name="${job_role_name:-${job_role_arn##*/}}"

missing=()
[[ -z "$region" ]] && missing+=("AWS_REGION/AWS_DEFAULT_REGION or terraform output region")
[[ -z "$cluster_name" ]] && missing+=("EMR_EKS_CLUSTER_NAME/EKS_CLUSTER_NAME or terraform output emr_eks_cluster_name")
[[ -z "$namespace" ]] && missing+=("EMR_EKS_NAMESPACE or terraform output emr_eks_namespace")
[[ -z "$job_role_arn" ]] && missing+=("EMR_EKS_JOB_ROLE_ARN or terraform output emr_eks_job_role_arn")

if ((${#missing[@]} > 0)); then
  echo "Missing required values:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 2
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required for EMR on EKS setup." >&2
  exit 2
fi

aws eks update-kubeconfig \
  --name "$cluster_name" \
  --region "$region" >/dev/null

if command -v kubectl >/dev/null 2>&1; then
  kubectl create namespace "$namespace" \
    --dry-run=client \
    -o yaml | kubectl apply -f -

  cat <<YAML | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: emr-containers
  namespace: $namespace
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get"]
  - apiGroups: [""]
    resources: ["serviceaccounts", "services", "configmaps", "events", "pods", "pods/log"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "deletecollection", "annotate", "patch", "label"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["create", "patch", "delete", "watch"]
  - apiGroups: ["apps"]
    resources: ["statefulsets", "deployments"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "annotate", "patch", "label"]
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "annotate", "patch", "label"]
  - apiGroups: ["extensions", "networking.k8s.io"]
    resources: ["ingresses"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "annotate", "patch", "label"]
  - apiGroups: ["rbac.authorization.k8s.io"]
    resources: ["roles", "rolebindings"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "deletecollection", "annotate", "patch", "label"]
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch", "describe", "create", "edit", "delete", "deletecollection", "annotate", "patch", "label"]
YAML

  cat <<YAML | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: emr-containers
  namespace: $namespace
subjects:
  - kind: User
    name: emr-containers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: emr-containers
  apiGroup: rbac.authorization.k8s.io
YAML
else
  echo "kubectl not found; skipping namespace creation for $namespace." >&2
fi

if command -v eksctl >/dev/null 2>&1; then
  eksctl create iamidentitymapping \
    --cluster "$cluster_name" \
    --namespace "$namespace" \
    --service-name "emr-containers" \
    --region "$region" \
    --approve >/dev/null || true
else
  account_id="$(aws sts get-caller-identity --query Account --output text)"
  partition="aws"
  service_linked_role_arn="arn:$partition:iam::$account_id:role/AWSServiceRoleForAmazonEMRContainers"
  aws iam create-service-linked-role \
    --aws-service-name emr-containers.amazonaws.com >/dev/null 2>&1 || true

  if command -v kubectl >/dev/null 2>&1 && kubectl -n kube-system get configmap aws-auth >/dev/null 2>&1; then
    current_map_roles="$(
      kubectl -n kube-system get configmap aws-auth \
        -o jsonpath='{.data.mapRoles}' 2>/dev/null || true
    )"
    if [[ "$current_map_roles" != *"AWSServiceRoleForAmazonEMRContainers"* ]]; then
      tmp_config="$(mktemp)"
      trap 'rm -f "$tmp_config"' EXIT
      kubectl -n kube-system get configmap aws-auth -o json >"$tmp_config"
      python3 - "$tmp_config" "$service_linked_role_arn" <<'PY' | kubectl apply -f -
import json
import sys

path, role_arn = sys.argv[1:]
config = json.loads(open(path, encoding="utf-8").read())
data = config.setdefault("data", {})
map_roles = data.get("mapRoles", "").rstrip()
entry = f"- rolearn: {role_arn}\n  username: emr-containers"
if role_arn not in map_roles:
    data["mapRoles"] = f"{map_roles}\n{entry}\n" if map_roles else f"{entry}\n"
print(json.dumps(config))
PY
    fi
  else
    echo "eksctl and aws-auth ConfigMap are unavailable; relying on EKS Access Entry integration during virtual cluster creation." >&2
  fi
fi

aws emr-containers update-role-trust-policy \
  --cluster-name "$cluster_name" \
  --namespace "$namespace" \
  --role-name "$job_role_name" \
  --region "$region" >/dev/null

cat <<EOF
EMR on EKS namespace prerequisites are ready.

Cluster       : $cluster_name
Namespace     : $namespace
Execution role: $job_role_arn

If Terraform has not registered the virtual cluster yet, run:

  terraform -chdir=infra/terraform apply \\
    -var enable_emr_eks=true \\
    -var emr_eks_cluster_name=$cluster_name \\
    -var emr_eks_namespace=$namespace \\
    -var emr_eks_job_role_arn=$job_role_arn
EOF
