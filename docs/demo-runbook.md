# KubePilot Final Demo Runbook

This runbook provides a repeatable evidence sequence without changing the live cluster. Run read-only commands from the repository root and keep GitHub live execution disabled unless a separately approved demonstration explicitly requires it.

## Evidence Safety

Before recording or taking screenshots, mask:

- AWS account IDs
- Public IP addresses and public DNS names
- IAM and resource ARNs
- GitHub, AWS, and Slack tokens
- Slack webhook URLs
- Signing secrets and other credentials

Review terminal scrollback, browser address bars, environment dumps, QR codes, and copied JSON before sharing evidence. Never use `env`, `set`, or credential-file output in a recording.

## Preflight

```bash
git branch --show-current
git status --short
aws sts get-caller-identity
aws configure get region
kubectl config current-context
```

Expected lab target:

- Region: `eu-west-3`
- Cluster: `kubepilot-eks-dev`
- Node group: three `t3.small` nodes

Screenshot suggestion: capture the branch and sanitized identity/context checks together. Mask the account number and ARN before sharing.

## 1. EKS Nodes

```bash
kubectl get nodes -o wide
kubectl top nodes
```

Show three Ready nodes and current utilization. Mask external or public addresses.

Screenshot suggestion: node readiness and capacity, with identifying network data cropped or masked.

## 2. ArgoCD Health

```bash
kubectl -n argocd get pods
kubectl -n argocd get applications.argoproj.io online-boutique
```

Show the ArgoCD components running and the `online-boutique` Application reporting `Synced` and `Healthy`. These commands are read-only.

Screenshot suggestion: the Application health row or sanitized ArgoCD UI application summary.

## 3. Online Boutique

```bash
kubectl -n default get deployments,services,pods
```

Show the Online Boutique workloads and service inventory. Do not expose a public load balancer hostname or IP in shared evidence.

Screenshot suggestion: workload readiness plus the application storefront in a separate browser capture.

## 4. SRE Incident Diagnosis

For a prepared demo incident, post the Alertmanager-shaped payload to the local KubePilot API. Replace the placeholders with an existing demonstration pod and container; do not create a new workload during this runbook.

```bash
curl -sS -X POST http://127.0.0.1:8000/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "firing",
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "KubePilotPodIncident",
        "namespace": "default",
        "pod": "DEMO_POD",
        "container": "DEMO_CONTAINER",
        "severity": "warning"
      },
      "annotations": {"summary": "KubePilot demo incident"}
    }]
  }'
```

If no prepared incident exists, demonstrate the deterministic and non-blocking paths with:

```bash
python -m pytest agent/tests/test_webhook.py -q
```

Screenshot suggestion: diagnosis, evidence, recommendation, and the safety fields showing no direct cluster write.

## 5. Human Approval

Keep `KUBEPILOT_GITHUB_LIVE_AUTHORIZED=false`. Demonstrate a signed Slack Approve or Reject callback in the prepared local/demo environment, or run the focused workflow tests:

```bash
python -m pytest agent/tests/test_slack_actions.py agent/tests/test_approval_webhook.py -q
```

Highlight signature verification, reviewer identity, idempotency, and the terminal approval state.

Screenshot suggestion: sanitized Slack decision and the matching KubePilot audit result. Mask webhook URLs, signatures, tokens, and user identifiers where required.

## 6. Safe GitHub Pull Request Path

Show the dry-run gateway and mocked executor tests without performing a GitHub write:

```bash
python -m pytest \
  agent/tests/test_sre_github_execution_gateway.py \
  agent/tests/test_sre_github_pr_executor.py \
  agent/tests/test_github_execution_gateway.py \
  agent/tests/test_github_pr_executor.py -q
```

Explain the delivery boundary:

```text
Human approval -> guarded GitHub branch and PR -> human merge -> ArgoCD -> Kubernetes
```

Screenshot suggestion: test result beside a previously approved, sanitized pull request. Do not expose tokens or private repository metadata.

## 7. FinOps Evidence

Review the checked-in real EKS samples:

```bash
sed -n '1,120p' docs/evidence/finops/README.md
sed -n '1,20p' docs/evidence/finops/finops-eks-summary.csv
```

Explain that CPU and memory are assessed together and that the short sample window supports demo validation, not production rightsizing.

Screenshot suggestion: the summary CSV and the documented `cartservice` high-memory safety example.

## 8. Metrics Endpoint

With the local API running:

```bash
curl -sS http://127.0.0.1:8000/metrics
```

Show incidents, approvals, rejections, PRs, GitHub failures, Slack callbacks, and LLM request counters.

Screenshot suggestion: a compact terminal capture containing metric names and representative values.

## 9. Grafana Dashboard

Validate the dashboard artifact without deploying Grafana:

```bash
python -m json.tool dashboards/kubepilot-operations.json > /dev/null
```

Review `dashboards/kubepilot-operations.json` in an existing Grafana environment only if a Prometheus datasource already scrapes KubePilot.

Screenshot suggestion: totals and activity-rate panels with datasource URLs and infrastructure identifiers hidden.

## 10. Kyverno Audit Policies

Render the CEL policy bundle locally:

```bash
kubectl kustomize gitops/security/kyverno > /dev/null
rg -n "validationActions|Audit" gitops/security/kyverno/*.yaml
```

Show that every resource is a `policies.kyverno.io/v1` `ValidatingPolicy` using only `Audit`. Do not install Kyverno or apply these manifests during the demo.

Screenshot suggestion: one policy's API, audit action, CEL validation, and namespace selector.

## 11. Security CI

Open `.github/workflows/trivy.yml` or the latest successful GitHub Actions run. Show both filesystem and IaC scans and their critical/high severity failure thresholds.

Screenshot suggestion: the sanitized workflow summary with both Trivy jobs visible.

## Closeout

Capture all evidence before considering cleanup. Then review costs with:

```bash
bash scripts/check-costs.sh
```

Do not run `scripts/cleanup.sh` during the demo. Cleanup is a separate operator action with identity, region, context, tag, Terraform-state, plan, and interactive confirmation guards.
