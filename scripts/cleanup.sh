#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-3}}"
CLUSTER_NAME="${KUBEPILOT_EKS_CLUSTER:-kubepilot-eks-dev}"
TF_DIR="${KUBEPILOT_TF_DIR:-infrastructure/terraform/eks}"
MODE="plan"

usage() {
  cat <<EOF
KubePilot guarded cleanup

Usage:
  ./scripts/cleanup.sh
  ./scripts/cleanup.sh --plan
  ./scripts/cleanup.sh --execute

Default mode:
  --plan

IMPORTANT:
  --execute may destroy the Terraform-managed KubePilot EKS infrastructure.

Safety requirements for --execute:
  1. KUBEPILOT_CLEANUP_EXECUTE=true
  2. Interactive confirmation
  3. Terraform performs its own final confirmation

Capture all demo evidence and screenshots BEFORE cleanup.
EOF
}

case "${1:-}" in
  "")
    ;;
  --plan)
    MODE="plan"
    ;;
  --execute)
    MODE="execute"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "ERROR: Unknown argument: $1"
    usage
    exit 1
    ;;
esac

echo "=================================================="
echo " KubePilot Guarded AWS Cleanup"
echo "=================================================="
echo
echo "Mode:         ${MODE}"
echo "Region:       ${REGION}"
echo "EKS cluster:  ${CLUSTER_NAME}"
echo "Terraform:    ${TF_DIR}"
echo
echo "WARNING:"
echo "Capture final demo evidence/screenshots BEFORE cleanup."
echo "This script must never be used for unrelated AWS resources."
echo

for command in aws terraform; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "ERROR: '${command}' is required but was not found in PATH."
    exit 1
  fi
done

if [[ ! -d "${TF_DIR}" ]]; then
  echo "ERROR: Terraform directory '${TF_DIR}' does not exist."
  exit 1
fi

if [[ ! -f "${TF_DIR}/main.tf" ]]; then
  echo "ERROR: '${TF_DIR}' does not look like the KubePilot EKS Terraform directory."
  exit 1
fi

echo "[1/5] AWS identity preflight"
AWS_ACCOUNT="$(
  aws sts get-caller-identity \
    --query 'Account' \
    --output text
)"

AWS_ARN="$(
  aws sts get-caller-identity \
    --query 'Arn' \
    --output text
)"

echo "Account: ${AWS_ACCOUNT}"
echo "Caller:  ${AWS_ARN}"

echo
echo "[2/5] AWS region preflight"
echo "Target region: ${REGION}"

CONFIGURED_REGION="$(
  aws configure get region 2>/dev/null || true
)"

if [[ -n "${CONFIGURED_REGION}" ]]; then
  echo "AWS CLI configured region: ${CONFIGURED_REGION}"

  if [[ "${CONFIGURED_REGION}" != "${REGION}" ]]; then
    echo
    echo "ERROR: Configured AWS region does not match target region."
    echo "Configured: ${CONFIGURED_REGION}"
    echo "Target:     ${REGION}"
    exit 1
  fi
else
  echo "No default AWS CLI region detected; using explicit region ${REGION}."
fi

echo
echo "[3/5] Kubernetes context preflight"

if command -v kubectl >/dev/null 2>&1; then
  CURRENT_CONTEXT="$(
    kubectl config current-context 2>/dev/null || true
  )"

  if [[ -n "${CURRENT_CONTEXT}" ]]; then
    echo "Current kubectl context: ${CURRENT_CONTEXT}"
  else
    echo "No active kubectl context."
  fi
else
  echo "kubectl is not installed; no Kubernetes context check performed."
fi

echo
echo "[4/5] Target EKS verification"

if ! aws eks describe-cluster \
  --region "${REGION}" \
  --name "${CLUSTER_NAME}" \
  --query 'cluster.{Name:name,Status:status,Version:version}' \
  --output table; then
  echo
  echo "ERROR: Target cluster '${CLUSTER_NAME}' could not be verified."
  echo "Cleanup aborted."
  exit 1
fi

echo
echo "[5/5] Terraform cleanup"

pushd "${TF_DIR}" >/dev/null

if [[ ! -d ".terraform" ]]; then
  echo
  echo "ERROR: Terraform has not been initialized in ${TF_DIR}."
  echo "Run terraform init manually and review the backend/state before retrying."
  popd >/dev/null
  exit 1
fi

echo
echo "Running Terraform destroy PLAN first..."
echo "No AWS resource will be destroyed by this plan command."
echo

terraform plan -destroy

if [[ "${MODE}" == "plan" ]]; then
  echo
  echo "=================================================="
  echo " PLAN COMPLETE - NO DESTRUCTION PERFORMED"
  echo "=================================================="
  echo
  echo "Review the plan carefully."
  echo "Use --execute only after final demo evidence is captured."
  popd >/dev/null
  exit 0
fi

if [[ "${KUBEPILOT_CLEANUP_EXECUTE:-}" != "true" ]]; then
  echo
  echo "ERROR: Destructive mode is not authorized."
  echo
  echo "To intentionally enable it, set:"
  echo "  KUBEPILOT_CLEANUP_EXECUTE=true"
  echo
  echo "Then run again with --execute."
  popd >/dev/null
  exit 1
fi

echo
echo "=================================================="
echo " DESTRUCTIVE ACTION REQUIRES CONFIRMATION"
echo "=================================================="
echo
echo "AWS account: ${AWS_ACCOUNT}"
echo "Region:      ${REGION}"
echo "Cluster:     ${CLUSTER_NAME}"
echo
echo "Type exactly:"
echo
echo "destroy ${CLUSTER_NAME} in ${REGION}"
echo

read -r -p "> " CONFIRMATION

EXPECTED="destroy ${CLUSTER_NAME} in ${REGION}"

if [[ "${CONFIRMATION}" != "${EXPECTED}" ]]; then
  echo
  echo "Confirmation did not match."
  echo "Cleanup aborted."
  popd >/dev/null
  exit 1
fi

echo
echo "Final Terraform confirmation follows."
echo "Review Terraform's resource list before confirming."
echo

terraform destroy

popd >/dev/null

echo
echo "=================================================="
echo " Terraform cleanup command completed"
echo "=================================================="
echo
echo "Review AWS manually to confirm only intended KubePilot"
echo "resources were removed."
