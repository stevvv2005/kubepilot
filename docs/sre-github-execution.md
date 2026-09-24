# SRE GitHub PR Execution

KubePilot SRE remediation remains GitOps-only. The SRE agent may read
Kubernetes state, render an approved manifest in memory, and create a GitHub
Pull Request. It must not write directly to Kubernetes or merge a Pull
Request.

## Flow

1. A deterministic SRE diagnosis produces a remediation proposal.
2. A human reviewer approves a specific value and audit context.
3. KubePilot renders the approved manifest in memory.
4. The SRE Git execution request is validated by the GitHub execution gateway.
5. When live execution is explicitly authorized, KubePilot creates a
   `fix/sre-*` branch, updates the allowlisted target file, commits, and opens
   a Pull Request.
6. A human reviews and merges the Pull Request. ArgoCD reconciles the cluster.

## Live Authorization

Live GitHub writes require a separate runtime authorization switch, for example
`KUBEPILOT_GITHUB_LIVE_AUTHORIZED=true`. The default must remain false.

Logical remediation approval alone is not enough to write to GitHub. Both the
human-approved request and live execution authorization are required.

## Safety Policy

The SRE GitHub execution path enforces:

- repository `stevvv2005/kubepilot`
- base branch `main`
- head branch prefix `fix/sre-`
- trusted SRE target-file allowlist
- non-empty rendered YAML
- explicit branch creation, file update, commit creation, branch publication,
  and Pull Request creation flags
- no direct cluster write flags

The executor uses an injected GitHub client and never calls Kubernetes. It does
not run `kubectl apply`, `kubectl patch`, `kubectl delete`, or any equivalent
cluster mutation.

## Dry-Run Versus Live

The existing SRE dry-run executor still describes the Git operations without
performing writes. The live SRE GitHub executor is a separate boundary and only
writes through GitHub after the safety gateway passes.

External GitHub failures should be returned as structured failures by the
calling workflow. They must not fall back to direct Kubernetes mutation.
