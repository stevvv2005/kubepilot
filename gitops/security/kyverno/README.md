# Kyverno Audit Policies

These manifests define read-only compliance checks for KubePilot workloads. They are deliberately disconnected from the live ArgoCD configuration and are not deployed by this repository state.

The bundle targets Kyverno's current CEL-based API:

- `apiVersion: policies.kyverno.io/v1`
- `kind: ValidatingPolicy`
- `spec.validationActions: [Audit]`

All findings are audit-only. Non-compliant resources remain admitted and are reported for review. The policies do not mutate, generate, verify, or delete resources, and they do not grant KubePilot any Kubernetes write capability.

## Policies

| Policy | Check |
| --- | --- |
| `kubepilot-require-resource-requests` | Requires CPU and memory requests on application and init containers. |
| `kubepilot-require-resource-limits` | Requires CPU and memory limits on application and init containers. |
| `kubepilot-disallow-privileged-containers` | Reports application, init, and ephemeral containers requesting privileged mode. |
| `kubepilot-disallow-host-path` | Reports Pods using `hostPath` volumes. |
| `kubepilot-require-run-as-non-root` | Requires Linux Pods to declare `runAsNonRoot: true` at Pod level or for every container. |
| `kubepilot-disallow-privilege-escalation` | Requires Linux application, init, and ephemeral containers to set `allowPrivilegeEscalation: false`. |

`readOnlyRootFilesystem` is intentionally not required in this baseline. Some otherwise legitimate workloads need writable runtime paths, and enabling it without workload-specific analysis would create excessive audit noise.

## Scope

Every policy uses a namespace selector to exclude these platform namespaces:

- `kube-system`
- `kube-public`
- `kube-node-lease`
- `argocd`
- `monitoring`
- `kyverno`

Application namespaces, including `default`, remain in scope. The non-root and privilege-escalation policies use CEL match conditions to evaluate Linux Pods only because those controls are operating-system specific.

## Future Installation

Kyverno would be installed later through a separately reviewed GitOps or Helm change that pins a compatible current version, installs the required CRDs and controllers, and accounts for cluster capacity. That deployment is outside this task because the current EKS cluster has only about two free Pod slots.

These manifests require a Kyverno release that supports the stable `policies.kyverno.io/v1` API. Confirm the selected release's Kubernetes compatibility before installation.

## Safe Validation And Promotion

Before any deployment or switch to blocking admission behavior:

1. Render the local bundle with `kubectl kustomize gitops/security/kyverno`.
2. Validate the CEL expressions with a compatible Kyverno CLI against representative compliant and non-compliant workload manifests in CI or an isolated non-production cluster.
3. Review generated policy reports over an agreed observation period.
4. Classify false positives and add narrowly scoped, documented exceptions only where necessary.
5. Re-run workload validation and obtain explicit security, platform, and workload-owner approval.
6. Promote one policy at a time through a separately reviewed Git change. KubePilot must never change policy behavior automatically.

Any switch from audit-only reporting to blocking behavior requires separate explicit review and approval. Do not run `kubectl apply` from this directory as part of validation; local rendering and offline policy tests are sufficient until installation and cluster capacity are separately approved.
