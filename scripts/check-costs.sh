#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-eu-west-3}}"
CLUSTER_NAME="${KUBEPILOT_EKS_CLUSTER:-kubepilot-eks-dev}"

echo "========================================"
echo " KubePilot AWS Cost / Resource Check"
echo "========================================"
echo
echo "This script is READ-ONLY."
echo "It does not create, modify, or delete AWS resources."
echo

if ! command -v aws >/dev/null 2>&1; then
  echo "ERROR: AWS CLI is not installed or not available in PATH."
  exit 1
fi

echo "[1/6] AWS caller identity"
aws sts get-caller-identity \
  --query '{Arn:Arn,Account:Account}' \
  --output table

echo
echo "[2/6] Region"
echo "Configured region: ${REGION}"

echo
echo "[3/6] EKS cluster"
if aws eks describe-cluster \
  --region "${REGION}" \
  --name "${CLUSTER_NAME}" \
  --query 'cluster.{Name:name,Status:status,Version:version}' \
  --output table 2>/dev/null; then
  :
else
  echo "KubePilot EKS cluster '${CLUSTER_NAME}' was not found or is not accessible."
fi

echo
echo "[4/6] EKS node groups"
NODEGROUPS="$(
  aws eks list-nodegroups \
    --region "${REGION}" \
    --cluster-name "${CLUSTER_NAME}" \
    --query 'nodegroups[]' \
    --output text 2>/dev/null || true
)"

if [[ -z "${NODEGROUPS}" ]]; then
  echo "No accessible node groups found."
else
  for NODEGROUP in ${NODEGROUPS}; do
    aws eks describe-nodegroup \
      --region "${REGION}" \
      --cluster-name "${CLUSTER_NAME}" \
      --nodegroup-name "${NODEGROUP}" \
      --query 'nodegroup.{Name:nodegroupName,Status:status,InstanceTypes:instanceTypes,Desired:scalingConfig.desiredSize,Min:scalingConfig.minSize,Max:scalingConfig.maxSize}' \
      --output table
  done
fi

echo
echo "[5/6] KubePilot-related load balancers"
aws elbv2 describe-load-balancers \
  --region "${REGION}" \
  --query 'LoadBalancers[].{Name:LoadBalancerName,Type:Type,State:State.Code,Scheme:Scheme}' \
  --output table 2>/dev/null || \
  echo "Unable to query ELBv2 resources."

echo
echo "[6/6] Cost Explorer (optional)"
echo "Cost Explorer requires billing permissions and may not be available."

START_DATE="$(date -u -d '7 days ago' +%Y-%m-%d 2>/dev/null || true)"
END_DATE="$(date -u +%Y-%m-%d 2>/dev/null || true)"

if [[ -n "${START_DATE}" && -n "${END_DATE}" ]]; then
  if aws ce get-cost-and-usage \
    --time-period "Start=${START_DATE},End=${END_DATE}" \
    --granularity DAILY \
    --metrics UnblendedCost \
    --query 'ResultsByTime[].{Date:TimePeriod.Start,Amount:Total.UnblendedCost.Amount,Unit:Total.UnblendedCost.Unit}' \
    --output table 2>/dev/null; then
    :
  else
    echo "Cost Explorer unavailable or permission denied."
  fi
else
  echo "Skipping Cost Explorer because compatible date command is unavailable."
fi

echo
echo "========================================"
echo " Read-only check complete"
echo "========================================"
echo
echo "Review the AWS Billing console before making cost decisions."
