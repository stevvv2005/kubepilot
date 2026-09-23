# KubePilot FinOps Runbooks

## Low Resource Utilization

A workload can be considered a rightsizing candidate when CPU and memory utilization remain significantly below configured requests.

KubePilot currently uses a simple heuristic based on observed utilization.

Before production use, rightsizing decisions should rely on longer historical windows and metrics such as p95 or p99 utilization.

Recommendations must remain advisory and require human approval.

## CPU Rightsizing

Compare CPU usage with CPU requests.

Avoid reducing CPU requests too aggressively based on a short observation window.

Use safety margins and historical usage before proposing production changes.

## Memory Rightsizing

Compare observed memory usage with memory requests and limits.

Memory reductions require caution because insufficient memory can cause OOMKilled events.

Human approval is required before preparing a GitOps change.

## Cost Estimation

Local OpenCost values are useful for development and testing.

They should not be treated as the exact AWS bill.

Cloud-provider pricing and real cluster costs should be used for production FinOps decisions.