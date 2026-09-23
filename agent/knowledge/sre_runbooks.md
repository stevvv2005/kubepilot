# KubePilot SRE Runbooks

## OOMKilled

An OOMKilled event indicates that a container exceeded its configured memory limit.

Recommended investigation:

- inspect current memory requests and limits
- inspect recent memory usage
- compare observed usage with configured limits
- verify whether the workload experienced a temporary spike
- review application logs
- avoid directly modifying the live Kubernetes resource

KubePilot should prepare a GitOps change proposal and require human approval before any resource configuration change.

## ImagePullBackOff

ImagePullBackOff means Kubernetes cannot pull the requested container image.

Recommended investigation:

- verify the image repository
- verify the image tag
- check imagePullSecrets
- inspect pod events
- verify registry accessibility

A missing or invalid image tag should be corrected through GitOps.

## Readiness Probe Failure

A readiness probe failure means the pod is not currently considered ready to receive traffic.

Recommended investigation:

- inspect the readiness probe configuration
- inspect application logs
- verify probe path and port
- verify startup timing
- inspect dependency availability

Do not automatically disable the readiness probe.
Prepare a safe GitOps recommendation and require human review.