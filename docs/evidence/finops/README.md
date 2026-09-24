# FinOps EKS Evidence

This directory contains real FinOps validation evidence collected from the KubePilot AWS EKS development cluster.

## Source

Cluster:
- EKS: `kubepilot-eks-dev`
- Region: `eu-west-3`

Metrics source:
- Kubernetes Metrics Server
- `kubectl top pods -n default`

## Files

### `finops-eks-samples.csv`

Contains 10 observation samples collected at approximately 30-second intervals for Online Boutique workloads.

Fields:
- timestamp
- pod
- CPU usage
- memory usage

### `finops-eks-summary.csv`

Contains the aggregated averages and maximum observed usage for each workload.

Fields include:
- workload/pod
- sample count
- average CPU
- maximum CPU
- average memory
- maximum memory

## Validation purpose

The dataset was used to validate the existing KubePilot FinOps engine against real EKS usage.

Validated flow:

Real EKS metrics
-> `WorkloadCostSnapshot`
-> FinOps utilization analysis
-> waste detection
-> rightsizing proposal
-> trusted GitOps target resolution
-> manifest inspection
-> GitOps diff
-> explicit human approval
-> approved manifest rendering in memory
-> Git commit plan
-> execution safety gateway
-> GitHub PR dry-run

No Kubernetes, AWS, Git, file, or GitHub write was performed during the FinOps dry-run validation.

## Important limitation

This is a short observation window used for project/demo validation.

It is NOT sufficient by itself for production-grade rightsizing.

Production recommendations should use a longer observation period and representative workload peaks, ideally through Prometheus, OpenCost, VPA recommendations, or equivalent historical telemetry.

## Key safety validation

`cartservice` demonstrated the importance of considering CPU and memory together:

- CPU utilization: approximately 3.2%
- Memory utilization: approximately 98.44%
- Result: NOT classified as waste

This prevented an unsafe memory rightsizing recommendation.
